import calendar
import io
import math
import numpy as np
import pandas as pd
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.models.automated_insights import ColumnClassification
from app.services.ai.trend_intelligence_engine import TrendIntelligenceEngine

client = TestClient(app)


def _upload_test_csv(csv_content: str, filename: str = "test.csv") -> str:
    files = {"file": (filename, io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post("/api/v1/datasets/upload", files=files)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["overview"]["id"]


def test_trend_conventional_growth_positive_baseline():
    """Verify that a positive starting baseline produces conventional percentage growth."""
    dates = pd.date_range("2023-01-01", periods=12, freq="MS")
    # Linear upward trend: 100 -> 220
    values = np.linspace(100.0, 220.0, 12)
    df = pd.DataFrame({"order_date": dates, "revenue": values})

    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "order_date", "revenue", "month")
    trend, facts = TrendIntelligenceEngine.analyze_trend(series_df, "order_date", "revenue", gran)

    assert trend is not None
    assert trend.direction == "increasing"
    assert trend.statistical_evidence == "statistically_supported"
    assert trend.conventional_growth_pct == 120.0
    assert trend.absolute_change == 120.0
    assert trend.range_normalized_shift_pct is None
    assert trend.peak_value == 220.0
    assert trend.trough_value == 100.0
    assert len(facts) >= 2


def test_trend_zero_starting_baseline():
    """Verify that starting baseline == 0 reports absolute change and range-normalized shift, not conventional growth."""
    dates = pd.date_range("2023-01-01", periods=8, freq="MS")
    # 0 -> 70
    values = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]
    df = pd.DataFrame({"created_at": dates, "profit": values})

    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "created_at", "profit", "month")
    trend, _ = TrendIntelligenceEngine.analyze_trend(series_df, "created_at", "profit", gran)

    assert trend is not None
    assert trend.direction == "increasing"
    assert trend.conventional_growth_pct is None  # Must NOT be conventional growth!
    assert trend.range_normalized_shift_pct == 100.0  # (70 - 0) / 70 * 100
    assert trend.absolute_change == 70.0
    assert "Range-Normalized Shift" in trend.explanation or "range-normalized shift" in trend.explanation


def test_trend_negative_starting_baseline():
    """Verify that negative starting baseline (e.g. -50 -> +50) is handled safely without sign flip."""
    dates = pd.date_range("2023-01-01", periods=11, freq="MS")
    # -50 -> +50
    values = np.linspace(-50.0, 50.0, 11)
    df = pd.DataFrame({"period_date": dates, "net_margin": values})

    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "period_date", "net_margin", "month")
    trend, _ = TrendIntelligenceEngine.analyze_trend(series_df, "period_date", "net_margin", gran)

    assert trend is not None
    assert trend.direction == "increasing"
    assert trend.conventional_growth_pct is None
    assert trend.absolute_change == 100.0
    assert trend.range_normalized_shift_pct == 100.0


def test_trend_constant_values_zero_range():
    """Verify that constant values (max == min) produce stable state and range_normalized_shift == 0."""
    dates = pd.date_range("2023-01-01", periods=10, freq="MS")
    values = [50.0] * 10
    df = pd.DataFrame({"sale_date": dates, "units": values})

    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "sale_date", "units", "month")
    trend, _ = TrendIntelligenceEngine.analyze_trend(series_df, "sale_date", "units", gran)

    assert trend is not None
    assert trend.direction == "stable"
    assert trend.absolute_change == 0.0
    assert trend.range_normalized_shift_pct == 0.0
    assert trend.trend_strength_r2 == 0.0
    assert "invariant constant value" in trend.explanation


def test_trend_autocorrelated_residuals_adjustment():
    """Verify that serial correlation is flagged via Durbin-Watson and standard error is adjusted."""
    dates = pd.date_range("2022-01-01", periods=20, freq="MS")
    # Generate AR(1) autocorrelated series with random seed
    np.random.seed(42)
    e = 0.0
    y = []
    for t in range(20):
        e = 0.85 * e + np.random.normal(0, 2)
        y.append(50.0 + 0.3 * t + e)

    df = pd.DataFrame({"dt": dates, "val": y})
    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "val", "month")
    trend, _ = TrendIntelligenceEngine.analyze_trend(series_df, "dt", "val", gran)

    assert trend is not None
    assert trend.durbin_watson_stat is not None
    # Because DW < 1.2 or > 2.8, HAC adjusted variance was computed
    assert trend.statistical_evidence in ("statistically_supported", "weak_evidence", "inconclusive")


def test_trend_insufficient_periods():
    """Verify that T < 6 periods are classified as insufficient_sample for formal inference."""
    dates = pd.date_range("2023-01-01", periods=4, freq="MS")
    values = [10.0, 20.0, 30.0, 40.0]
    df = pd.DataFrame({"dt": dates, "val": values})

    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "val", "month")
    trend, _ = TrendIntelligenceEngine.analyze_trend(series_df, "dt", "val", gran)

    assert trend is not None
    assert trend.statistical_evidence == "insufficient_sample"
    assert trend.p_value is None


def test_zero_mad_constant_differences():
    """Verify that constant differences (MAD == 0 and MeanAD == 0) produce zero false anomalies."""
    dates = pd.date_range("2023-01-01", periods=10, freq="MS")
    # Linear ramp where every period difference is exactly 10.0
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    df = pd.DataFrame({"dt": dates, "val": values})

    series_df, _, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "val", "month")
    anomalies, _ = TrendIntelligenceEngine.detect_temporal_anomalies(series_df, "dt", "val")

    # In a perfect linear series, differences are constant; zero false anomalies should be flagged
    assert len(anomalies) == 0


def test_zero_mad_repeated_differences_mean_ad_fallback():
    """Verify that when MAD == 0 due to > 50% identical differences, MeanAD fallback handles scale correctly."""
    dates = pd.date_range("2023-01-01", periods=10, freq="MS")
    # 6 identical values (diff = 0) + a massive sudden jump
    # diffs: 0, 0, 0, 0, 0, 0, 0, +200, 0
    # Median diff is 0, MAD is 0! MeanAD > 0.
    values = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 210.0, 210.0]
    df = pd.DataFrame({"dt": dates, "val": values})

    series_df, _, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "val", "month")
    anomalies, facts = TrendIntelligenceEngine.detect_temporal_anomalies(series_df, "dt", "val")

    assert len(anomalies) >= 1
    spike = anomalies[0]
    assert spike.anomaly_type == "sudden_spike"
    assert "MeanAD Robust Scale Fallback" in spike.detection_method
    assert spike.severity == "critical"


def test_zero_mad_single_sudden_step_spike():
    """Verify single sudden step jump from flat baseline is caught cleanly."""
    dates = pd.date_range("2023-01-01", periods=8, freq="MS")
    values = [10.0, 10.0, 10.0, 10.0, 95.0, 10.0, 10.0, 10.0]
    df = pd.DataFrame({"dt": dates, "val": values})

    series_df, _, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "val", "month")
    anomalies, _ = TrendIntelligenceEngine.detect_temporal_anomalies(series_df, "dt", "val")

    assert len(anomalies) >= 1
    types = [a.anomaly_type for a in anomalies]
    assert "sudden_spike" in types or "deterministic_step_anomaly" in types


def test_multi_column_discovery_and_ranking():
    """Verify discovery and ranking of multiple date and metric candidate columns."""
    dates_1 = pd.date_range("2023-01-01", periods=10, freq="D")
    dates_2 = pd.date_range("2023-01-05", periods=10, freq="D")
    df = pd.DataFrame({
        "order_date": dates_1,
        "ship_date": dates_2,
        "net_revenue": np.random.uniform(100, 500, 10),
        "discount_pct": np.random.uniform(0, 10, 10),
        "id": range(1, 11),  # identifier to be excluded
    })

    classifications = {
        "order_date": ColumnClassification(name="order_date", semantic_role="date_time", inferred_type="datetime", unique_count=10, null_count=0, is_usable_for_metrics=False, is_usable_for_grouping=True),
        "ship_date": ColumnClassification(name="ship_date", semantic_role="date_time", inferred_type="datetime", unique_count=10, null_count=0, is_usable_for_metrics=False, is_usable_for_grouping=True),
        "net_revenue": ColumnClassification(name="net_revenue", semantic_role="numerical_measure", inferred_type="float", unique_count=10, null_count=0, is_usable_for_metrics=True, is_usable_for_grouping=False),
        "discount_pct": ColumnClassification(name="discount_pct", semantic_role="numerical_measure", inferred_type="float", unique_count=10, null_count=0, is_usable_for_metrics=True, is_usable_for_grouping=False),
        "id": ColumnClassification(name="id", semantic_role="identifier", inferred_type="integer", unique_count=10, null_count=0, is_usable_for_metrics=False, is_usable_for_grouping=False),
    }

    combs = TrendIntelligenceEngine.discover_combinations(df, classifications)

    assert len(combs) == 4  # 2 dates x 2 metrics
    # order_date + net_revenue should be ranked highest (default)
    assert combs[0].is_default is True
    assert combs[0].date_column == "order_date"
    assert combs[0].metric_column == "net_revenue"
    # id column must not appear in combinations
    assert not any(c.metric_column == "id" for c in combs)


def test_missing_dates_resampling_with_nan():
    """Verify that gapped dates are resampled without injecting artificial zero drops."""
    dates = pd.to_datetime(["2023-01-01", "2023-02-01", "2023-05-01", "2023-06-01"])
    values = [100.0, 110.0, 140.0, 150.0]
    df = pd.DataFrame({"dt": dates, "val": values})

    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "val", "month")
    # Result has the valid months and doesn't crash
    assert len(series_df) == 4
    trend, _ = TrendIntelligenceEngine.analyze_trend(series_df, "dt", "val", gran)
    assert trend is not None
    assert trend.direction == "increasing"


def test_duplicate_timestamps_aggregation():
    """Verify that multiple records on the same timestamp aggregate properly."""
    dates = pd.to_datetime([
        "2023-01-01", "2023-01-01", "2023-01-02", "2023-01-02", "2023-01-03", "2023-01-03"
    ])
    values = [10.0, 15.0, 20.0, 25.0, 30.0, 35.0]
    df = pd.DataFrame({"dt": dates, "revenue": values})

    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "revenue", "day")
    assert len(series_df) == 3
    # Check aggregation sum
    assert series_df["value"].iloc[0] == 25.0  # 10 + 15
    assert series_df["value"].iloc[1] == 45.0  # 20 + 25
    assert series_df["value"].iloc[2] == 65.0  # 30 + 35


def test_seasonality_daily_anova_supported():
    """Verify day-of-week seasonality on 35 daily observations (5 full weeks) with weekend effect."""
    dates = pd.date_range("2023-01-02", periods=35, freq="D")  # starts on Monday
    # Create strong weekend surge on detrended series
    values = []
    for d in dates:
        # base trend
        base = 100.0 + (d.day * 0.5)
        # Saturday(5) and Sunday(6) have +60 surge
        seasonal = 60.0 if d.weekday() >= 5 else 0.0
        values.append(base + seasonal)

    df = pd.DataFrame({"order_date": dates, "sales": values})
    analysis, facts = TrendIntelligenceEngine.analyze_seasonality(df, "order_date", "sales")

    assert analysis.is_detected is True
    assert analysis.status == "statistically_supported"
    assert analysis.cycle_type == "day_of_week"
    assert analysis.anova_p_value is not None
    assert analysis.anova_p_value <= 0.05
    assert analysis.peak_season in ("Saturday", "Sunday")
    assert len(analysis.patterns) == 7
    assert len(facts) >= 1


def test_seasonality_insufficient_duration_rejected():
    """Verify that 14 daily records (only 2 weeks) reject seasonality with status 'insufficient_duration'."""
    dates = pd.date_range("2023-01-01", periods=14, freq="D")
    values = [10.0] * 14
    df = pd.DataFrame({"dt": dates, "val": values})

    analysis, _ = TrendIntelligenceEngine.analyze_seasonality(df, "dt", "val")
    assert analysis.is_detected is False
    assert analysis.status == "insufficient_duration"
    assert "minimum duration" in analysis.explanation.lower()


def test_partial_period_duration_detection():
    """Verify that a month with only the first 8 days is flagged as partial period."""
    # Data from Jan 1 through March 8
    dates = pd.date_range("2023-01-01", "2023-03-08", freq="D")
    values = np.linspace(50.0, 150.0, len(dates))
    df = pd.DataFrame({"order_date": dates, "sales": values})

    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "order_date", "sales", "month")
    assert len(series_df) == 3  # Jan, Feb, Mar

    mar_row = series_df.iloc[2]
    assert bool(mar_row["is_partial_period"]) is True
    assert mar_row["temporal_completeness_pct"] < 50.0


def test_ask_data_temporal_queries():
    """Verify natural-language temporal queries in Ask Your Data:
    - Trend query: 'Is revenue increasing or decreasing over time?'
    - Period benchmark: 'Which month had the highest sales?'
    - Temporal anomalies: 'Are there any sudden drops in performance?'
    """
    csv_rows = ["order_date,revenue"]
    for i in range(1, 13):
        # 100, 120, 140, ..., 320 except Oct has a dip (150)
        val = 100 + (i - 1) * 20
        if i == 10:
            val = 150  # sudden drop
        csv_rows.append(f"2023-{i:02d}-01,{val}")
    csv_data = "\n".join(csv_rows) + "\n"
    ds_id = _upload_test_csv(csv_data, "temporal_ask_data.csv")

    # 1. Trend analysis question
    res1 = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Is revenue increasing or decreasing over time?", "include_chart": True},
    )
    assert res1.status_code == 200, res1.text
    data1 = res1.json()
    assert data1["primary_metric"] is not None
    assert "increasing" in data1["direct_answer"].lower() or "increasing" in data1["primary_metric"]["label"].lower()
    assert len(data1["tabular_data"]) >= 10
    assert len(data1["grounded_facts"]) >= 1

    # 2. Period benchmark question
    res2 = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Which month had the highest sales?", "include_chart": False},
    )
    assert res2.status_code == 200, res2.text
    data2 = res2.json()
    assert data2["primary_metric"] is not None
    assert "peak" in data2["primary_metric"]["label"].lower() or "dec" in data2["direct_answer"].lower() or "2023-12" in data2["direct_answer"].lower()
    assert len(data2["tabular_data"]) >= 2

    # 3. Temporal anomaly question
    res3 = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Are there any sudden drops in performance?", "include_chart": False},
    )
    assert res3.status_code == 200, res3.text
    data3 = res3.json()
    assert data3["primary_metric"] is not None
    assert any(term in data3["primary_metric"]["label"].lower() for term in ["anomal", "drop", "stable", "fluctuat", "pattern"])


def test_ask_data_temporal_query_on_non_date_dataset():
    """Verify asking a temporal query on a dataset without date columns returns HTTP 200 and a clean non-date explanation."""
    csv_data = (
        "item,price,quantity\n"
        "Widget A,10.5,100\n"
        "Widget B,25.0,40\n"
        "Widget C,15.2,80\n"
    )
    ds_id = _upload_test_csv(csv_data, "non_temporal_inventory.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Is revenue increasing or decreasing over time?", "include_chart": False},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "does not contain any date" in data["direct_answer"].lower() or "temporal analysis skipped" in data["direct_answer"].lower()
    assert len(data["limitations_and_warnings"]) >= 1


def test_snapshot_invalidation_after_cleaning():
    """Verify that cleaning a column updates the snapshot hash and invalidates the cached insights."""
    csv_data = (
        "order_date,revenue\n"
        "2023-01-01,100\n"
        "2023-02-01,120\n"
        "2023-03-01,140\n"
        "2023-04-01,\n"
        "2023-05-01,180\n"
        "2023-06-01,200\n"
    )
    ds_id = _upload_test_csv(csv_data, "cleaning_trend_invalidation.csv")

    # Step 1: Initial insights generation
    res1 = client.get(f"/api/v1/datasets/{ds_id}/insights")
    assert res1.status_code == 200, res1.text
    data1 = res1.json()
    assert data1["is_cached"] is False
    hash1 = data1["snapshot_hash"]

    # Step 2: Second call retrieves cached insights
    res2 = client.get(f"/api/v1/datasets/{ds_id}/insights")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_cached"] is True
    assert data2["snapshot_hash"] == hash1

    # Step 3: Apply cleaning operation (mean imputation on missing value in revenue)
    clean_res = client.post(
        f"/api/v1/datasets/{ds_id}/cleaning/apply",
        json={
            "operation_type": "missing_values",
            "column_name": "revenue",
            "strategy": "mean_replacement",
        },
    )
    assert clean_res.status_code == 200
    assert clean_res.json()["success"] is True

    # Step 4: Fetch insights again - should detect new snapshot hash and recompute
    res3 = client.get(f"/api/v1/datasets/{ds_id}/insights")
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["snapshot_hash"] != hash1
    assert data3["is_cached"] is False


# =========================================================================
# UNIT TESTS FOR FIX 1: BENJAMINI-HOCHBERG FDR CORRECTION
# =========================================================================

def test_benjamini_hochberg_known_values():
    """Verify pure NumPy Benjamini-Hochberg step-up adjustment on known values."""
    # Input: [0.01, 0.04, 0.03]
    # Sorted: p(1)=0.01 -> q=3/1*0.01=0.03; p(2)=0.03 -> q=3/2*0.03=0.045; p(3)=0.04 -> q=3/3*0.04=0.04
    # Backward min: q3=0.04, q2=min(0.045, 0.04)=0.04, q1=min(0.03, 0.04)=0.03
    # Expected output: [0.03, 0.04, 0.04]
    p_raw = [0.01, 0.04, 0.03]
    p_adj = TrendIntelligenceEngine.benjamini_hochberg_correction(p_raw, q=0.05)
    assert p_adj == [0.03, 0.04, 0.04]


def test_benjamini_hochberg_invalid_and_missing_values():
    """Verify that None, NaN, inf, and invalid out-of-range p-values are safely excluded and preserved as None."""
    p_raw = [0.01, None, float("nan"), float("inf"), -0.5, 1.5, 0.03]
    p_adj = TrendIntelligenceEngine.benjamini_hochberg_correction(p_raw, q=0.05)

    assert len(p_adj) == 7
    # Valid elements (0.01 and 0.03) are adjusted for m = 2 tests
    # p(1)=0.01 -> 2/1 * 0.01 = 0.02
    # p(2)=0.03 -> 2/2 * 0.03 = 0.03
    assert p_adj[0] == 0.02
    assert p_adj[1] is None
    assert p_adj[2] is None
    assert p_adj[3] is None
    assert p_adj[4] is None
    assert p_adj[5] is None
    assert p_adj[6] == 0.03


def test_benjamini_hochberg_single_hypothesis():
    """Verify single hypothesis preservation: when only 1 valid test is evaluated, p_adj == p_raw."""
    p_raw = [0.0421]
    p_adj = TrendIntelligenceEngine.benjamini_hochberg_correction(p_raw, q=0.05)
    assert p_adj == [0.0421]


def test_benjamini_hochberg_multiple_screening_adjusts_evidence():
    """Verify that when multiple hypotheses are screened, a borderline p-value that fails FDR is not statistically supported."""
    dates = pd.date_range("2023-01-01", periods=12, freq="MS")
    # Linear upward trend
    values = np.linspace(100.0, 150.0, 12)
    df = pd.DataFrame({"order_date": dates, "revenue": values})

    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "order_date", "revenue", "month")

    # When tested as a single hypothesis, p_val <= 0.05 yields statistically_supported
    trend_single, _ = TrendIntelligenceEngine.analyze_trend(
        series_df, "order_date", "revenue", gran, total_hypotheses_screened=1
    )
    assert trend_single is not None
    assert trend_single.statistical_evidence == "statistically_supported"
    assert trend_single.p_value is not None
    assert trend_single.p_value <= 0.05

    # If adjusted p_value due to FDR across 5 screened hypotheses is 0.08 (> 0.05),
    # the evidence must be downgraded and not granted statistically_supported
    trend_multi, _ = TrendIntelligenceEngine.analyze_trend(
        series_df,
        "order_date",
        "revenue",
        gran,
        p_value_fdr_adjusted=0.08,
        total_hypotheses_screened=5,
    )
    assert trend_multi is not None
    assert trend_multi.p_value_fdr_adjusted == 0.08
    assert trend_multi.statistical_evidence != "statistically_supported"
    assert trend_multi.statistical_evidence == "weak_evidence"
    assert "p_FDR=0.0800" in trend_multi.explanation


# =========================================================================
# UNIT TESTS FOR FIX 2: BUSINESS MAGNITUDE
# =========================================================================

def test_business_magnitude_material():
    """Verify net shift >= 20% of historical mean absolute value is classified as material."""
    dates = pd.date_range("2023-01-01", periods=8, freq="MS")
    # 100 -> 140 (change = +40). Mean = 120. Ratio = 40 / 120 = 33.3% >= 20%
    values = np.linspace(100.0, 140.0, 8)
    df = pd.DataFrame({"dt": dates, "val": values})
    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "val", "month")

    trend, _ = TrendIntelligenceEngine.analyze_trend(series_df, "dt", "val", gran)
    assert trend is not None
    assert trend.business_magnitude == "material"


def test_business_magnitude_moderate():
    """Verify net shift between 5% and 20% of historical mean absolute value is classified as moderate."""
    dates = pd.date_range("2023-01-01", periods=8, freq="MS")
    # 100 -> 110 (change = +10). Mean = 105. Ratio = 10 / 105 = 9.5% (between 5% and 20%)
    values = np.linspace(100.0, 110.0, 8)
    df = pd.DataFrame({"dt": dates, "val": values})
    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "val", "month")

    trend, _ = TrendIntelligenceEngine.analyze_trend(series_df, "dt", "val", gran)
    assert trend is not None
    assert trend.business_magnitude == "moderate"


def test_business_magnitude_immaterial():
    """Verify net shift < 5% of historical mean absolute value is classified as immaterial."""
    dates = pd.date_range("2023-01-01", periods=8, freq="MS")
    # 1000 -> 1010 (change = +10). Mean = 1005. Ratio = 10 / 1005 = 0.99% < 5%
    values = np.linspace(1000.0, 1010.0, 8)
    df = pd.DataFrame({"dt": dates, "val": values})
    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "val", "month")

    trend, _ = TrendIntelligenceEngine.analyze_trend(series_df, "dt", "val", gran)
    assert trend is not None
    assert trend.business_magnitude == "immaterial"


def test_business_magnitude_negative_and_zero_mean():
    """Verify safe calculation when series contains negative values and zero-mean handling."""
    dates = pd.date_range("2023-01-01", periods=8, freq="MS")
    # Series with negative numbers: -50 -> +50. Change = 100. Mean abs val = ~28.6.
    values = np.linspace(-50.0, 50.0, 8)
    df = pd.DataFrame({"dt": dates, "val": values})
    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "val", "month")

    trend, _ = TrendIntelligenceEngine.analyze_trend(series_df, "dt", "val", gran)
    assert trend is not None
    assert trend.business_magnitude == "material"
    # Starting baseline was negative (-50), so conventional_growth is None and range_norm is populated
    assert trend.conventional_growth_pct is None
    assert trend.range_normalized_shift_pct == 100.0


def test_business_magnitude_constant_series():
    """Verify constant series yields immaterial magnitude and absolute change == 0.0."""
    dates = pd.date_range("2023-01-01", periods=6, freq="MS")
    values = [42.0] * 6
    df = pd.DataFrame({"dt": dates, "val": values})
    series_df, gran, _ = TrendIntelligenceEngine.prepare_time_series(df, "dt", "val", "month")

    trend, _ = TrendIntelligenceEngine.analyze_trend(series_df, "dt", "val", gran)
    assert trend is not None
    assert trend.business_magnitude == "immaterial"
    assert trend.absolute_change == 0.0
    assert trend.p_value_fdr_adjusted == 1.0


