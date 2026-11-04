import calendar
import math
import uuid
from typing import Any, Dict, List, Literal, Optional, Tuple
import numpy as np
import pandas as pd

from app.core.json_encoder import sanitize_for_json
from app.models.ask_data import QueryResultFact
from app.models.automated_insights import (
    ColumnClassification,
    DateGranularity,
    DateMetricCombination,
    PeriodDataPoint,
    SeasonalPattern,
    SeasonalityAnalysis,
    SeasonalityStatus,
    StatisticalEvidence,
    TemporalAnomaly,
    TrendAnalysis,
    TrendDirection,
)
from app.models.dashboard import ChartConfig

THEME_COLORS = [
    "#8b7cff",  # electric purple / primary accent
    "#36c9f4",  # cyan / accent-2
    "#34d399",  # emerald green / peak
    "#f43f5e",  # rose / trough
    "#fbbf24",  # amber / anomaly
    "#a78bfa",  # light purple
    "#60a5fa",  # blue
    "#fb923c",  # orange
]


class TrendIntelligenceEngine:
    """
    Pandas & NumPy analytical engine for AutoAnalyst AI Phase 4.4.
    Autonomously discovers temporal trends, validates OLS significance with HAC/autocorrelation,
    detects sudden anomalies via Zero-MAD robust scaling, performs detrended ANOVA seasonality,
    and disambiguates chronological vs cyclical period benchmarks.
    """

    # Priority keywords for candidate ranking
    PREFERRED_DATE_NAMES = {"date", "order_date", "created_at", "timestamp", "datetime", "sale_date", "invoice_date"}
    PREFERRED_METRIC_NAMES = {"revenue", "sales", "profit", "amount", "total", "cost", "income", "volume", "turnover"}

    # =========================================================================
    # STATISTICAL HELPER FUNCTIONS (Pure Python & NumPy, zero scipy dependency)
    # =========================================================================
    @staticmethod
    def _betacf(a: float, b: float, x: float) -> float:
        """Continued fraction for incomplete beta function (Lentz's method)."""
        max_iter = 100
        eps = 3.0e-7
        fpmin = 1.0e-30
        qab = a + b
        qap = a + 1.0
        qam = a - 1.0
        c = 1.0
        d = 1.0 - qab * x / qap
        if abs(d) < fpmin:
            d = fpmin
        d = 1.0 / d
        h = d
        for m in range(1, max_iter + 1):
            m2 = 2 * m
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = 1.0 + aa * d
            if abs(d) < fpmin:
                d = fpmin
            c = 1.0 + aa / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1.0 / d
            h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = 1.0 + aa * d
            if abs(d) < fpmin:
                d = fpmin
            c = 1.0 + aa / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1.0 / d
            del_val = d * c
            h *= del_val
            if abs(del_val - 1.0) <= eps:
                break
        return h

    @classmethod
    def _inc_beta(cls, a: float, b: float, x: float) -> float:
        """Regularized incomplete beta function I_x(a, b)."""
        if x <= 0.0:
            return 0.0
        if x >= 1.0:
            return 1.0
        bt = math.exp(
            math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
            + a * math.log(x) + b * math.log(1.0 - x)
        )
        if x < (a + 1.0) / (a + b + 2.0):
            return bt * cls._betacf(a, b, x) / a
        else:
            return 1.0 - bt * cls._betacf(b, a, 1.0 - x) / b

    @classmethod
    def _student_t_pvalue(cls, t_stat: float, df: int) -> float:
        """Two-tailed p-value for Student's t distribution with df degrees of freedom."""
        if df <= 0 or math.isnan(t_stat):
            return 1.0
        t2 = t_stat * t_stat
        x = df / (df + t2)
        p = cls._inc_beta(df / 2.0, 0.5, x)
        return max(0.0, min(1.0, float(p)))

    @classmethod
    def _f_distribution_pvalue(cls, f_stat: float, df1: int, df2: int) -> float:
        """Right-tailed p-value for F distribution P(F >= f_stat)."""
        if df1 <= 0 or df2 <= 0 or f_stat <= 0.0 or math.isnan(f_stat):
            return 1.0
        x = (df1 * f_stat) / (df1 * f_stat + df2)
        p = 1.0 - cls._inc_beta(df1 / 2.0, df2 / 2.0, x)
        return max(0.0, min(1.0, float(p)))

    @classmethod
    def _chi2_pvalue(cls, chi2_stat: float, df: int) -> float:
        """Right-tailed p-value for Chi-squared distribution P(X >= chi2_stat)."""
        if df <= 0 or chi2_stat <= 0.0 or math.isnan(chi2_stat):
            return 1.0
        s = chi2_stat / df
        z = (s ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df))) / math.sqrt(2.0 / (9.0 * df))
        p = 0.5 * (1.0 - math.erf(z / math.sqrt(2.0)))
        return max(0.0, min(1.0, float(p)))

    # =========================================================================
    # 1. CANDIDATE DISCOVERY & COMBINATION RANKING
    # =========================================================================
    @classmethod
    def discover_combinations(
        cls,
        df: pd.DataFrame,
        classifications: Dict[str, ColumnClassification],
    ) -> List[DateMetricCombination]:
        """
        Discovers all valid (DateTime, NumericalMeasure) combinations in the dataset,
        excluding technical identifiers, URLs, and constant columns, and ranks them by analytical relevance.
        """
        date_candidates = []
        for col_name, c in classifications.items():
            if c.semantic_role == "date_time":
                date_candidates.append(col_name)
            elif c.inferred_type == "datetime":
                date_candidates.append(col_name)
            elif c.semantic_role not in ("identifier", "url_media") and any(w in col_name.lower() for w in ("date", "time", "timestamp")):
                # Verify parseability on sample
                sample = df[col_name].dropna().head(20)
                if len(sample) >= 3:
                    try:
                        parsed = pd.to_datetime(sample, errors="coerce")
                        if parsed.notna().mean() >= 0.70 and parsed.nunique() >= 3:
                            date_candidates.append(col_name)
                    except Exception:
                        pass

        # Exclude identifiers and columns not suitable for business metrics
        metric_candidates = [
            c.name for c in classifications.values()
            if c.semantic_role == "numerical_measure"
            and c.is_usable_for_metrics
            and df[c.name].dropna().nunique() > 1
        ]

        if not date_candidates or not metric_candidates:
            return []

        # Sort date candidates: preferred names first
        date_candidates.sort(
            key=lambda d: any(k in d.lower() for k in cls.PREFERRED_DATE_NAMES),
            reverse=True,
        )

        # Sort metric candidates: preferred business revenue/sales first
        metric_candidates.sort(
            key=lambda m: any(k in m.lower() for k in cls.PREFERRED_METRIC_NAMES),
            reverse=True,
        )

        combinations: List[DateMetricCombination] = []
        is_first = True

        for date_col in date_candidates:
            for metric_col in metric_candidates:
                comb_id = f"{date_col}__{metric_col}"
                # Sample granularity determination
                valid_dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
                if len(valid_dates) < 3:
                    continue

                min_date = valid_dates.min()
                max_date = valid_dates.max()
                span_days = (max_date - min_date).days

                if span_days > 365 * 3:
                    gran: DateGranularity = "year"
                elif span_days > 180:
                    gran = "month"
                elif span_days > 21:
                    gran = "week"
                else:
                    gran = "day"

                display = f"{metric_col.replace('_', ' ').title()} over {date_col.replace('_', ' ').title()} ({gran.capitalize()})"
                combinations.append(
                    DateMetricCombination(
                        combination_id=comb_id,
                        date_column=date_col,
                        metric_column=metric_col,
                        granularity=gran,
                        total_periods=len(valid_dates),
                        is_default=is_first,
                        display_label=display,
                    )
                )
                is_first = False

        return combinations

    # =========================================================================
    # 1B. MULTIPLE HYPOTHESIS TESTING (BENJAMINI-HOCHBERG FDR CORRECTION)
    # =========================================================================
    @classmethod
    def benjamini_hochberg_correction(
        cls,
        p_values: List[Optional[float]],
        q: float = 0.05,
    ) -> List[Optional[float]]:
        """
        Pure NumPy implementation of the Benjamini-Hochberg (1995) step-up procedure.
        Handles None, NaN, infinite, and invalid p-values safely by excluding them
        from ranking and preserving their unavailable status in the output.
        Returns adjusted p-values corresponding to each original input position.
        When only 1 valid p-value is provided (single hypothesis), p_adj = p_raw.
        """
        n = len(p_values)
        if n == 0:
            return []

        # Filter valid p-values: finite numbers in [0.0, 1.0]
        valid_indices: List[int] = []
        valid_p_vals: List[float] = []

        for idx, p in enumerate(p_values):
            if p is not None:
                try:
                    p_float = float(p)
                    if not math.isnan(p_float) and not math.isinf(p_float) and 0.0 <= p_float <= 1.0:
                        valid_indices.append(idx)
                        valid_p_vals.append(p_float)
                except (ValueError, TypeError):
                    pass

        m = len(valid_p_vals)
        result: List[Optional[float]] = [None] * n

        if m == 0:
            return result

        if m == 1:
            # Single hypothesis: no multiple testing penalty
            result[valid_indices[0]] = round(valid_p_vals[0], 4)
            return result

        # Sort valid p-values ascending
        sort_order = np.argsort(valid_p_vals)
        sorted_p = np.array(valid_p_vals)[sort_order]

        # Step-up adjustment: q_k = (m / k) * p_(k) for k = 1..m
        k_ranks = np.arange(1, m + 1, dtype=float)
        adj_p = (float(m) / k_ranks) * sorted_p

        # Monotonicity enforcement from back to front: p_adj(k) = min(q_k, p_adj(k+1))
        for i in range(m - 2, -1, -1):
            if adj_p[i] > adj_p[i + 1]:
                adj_p[i] = adj_p[i + 1]

        # Bound within [0.0, 1.0]
        adj_p = np.clip(adj_p, 0.0, 1.0)

        # Map back to original indices
        for i, orig_sort_idx in enumerate(sort_order):
            actual_orig_idx = valid_indices[orig_sort_idx]
            result[actual_orig_idx] = round(float(adj_p[i]), 4)

        return result

    @classmethod
    def screen_combinations_fdr(
        cls,
        df: pd.DataFrame,
        combinations: List[DateMetricCombination],
        q: float = 0.05,
    ) -> Dict[str, Tuple[Optional[float], Optional[float]]]:
        """
        Screens preliminary trend p-values across all eligible date/metric combinations
        and applies Benjamini-Hochberg FDR correction.
        Returns a mapping: combination_id -> (p_value_raw, p_value_fdr_adjusted).
        """
        if not combinations:
            return {}

        raw_p_list: List[Optional[float]] = []

        for comb in combinations:
            try:
                series_df, gran, _ = cls.prepare_time_series(
                    df=df,
                    date_col=comb.date_column,
                    metric_col=comb.metric_column,
                    granularity=comb.granularity,
                )
                if len(series_df) < 6:
                    raw_p_list.append(None)
                    continue

                y_vals = series_df["value"].to_numpy(dtype=float)
                T = len(y_vals)
                y_max = float(np.max(y_vals))
                y_min = float(np.min(y_vals))
                if y_max - y_min == 0.0:
                    raw_p_list.append(1.0)
                    continue

                t_index = np.arange(1, T + 1, dtype=float)
                t_bar = np.mean(t_index)
                denom = np.sum((t_index - t_bar) ** 2)
                y_mean = float(np.mean(y_vals))
                slope = float(np.sum((t_index - t_bar) * (y_vals - y_mean)) / denom) if denom != 0 else 0.0
                intercept = float(y_mean - slope * t_bar)
                residuals = y_vals - (intercept + slope * t_index)
                ss_res = float(np.sum(residuals ** 2))

                # Autocorrelation
                diff_res = np.diff(residuals)
                dw_stat = float(np.sum(diff_res ** 2) / max(ss_res, 1e-9))

                var_ols = (ss_res / max(T - 2, 1)) / max(denom, 1e-9)
                se_beta = math.sqrt(max(var_ols, 1e-12))

                if dw_stat < 1.2 or dw_stat > 2.8:
                    bandwidth = max(1, int(0.75 * (T ** (1.0 / 3.0))))
                    w_t = t_index - t_bar
                    gamma_0 = np.sum((w_t ** 2) * (residuals ** 2))
                    gamma_sum = 0.0
                    for lag in range(1, bandwidth + 1):
                        weight = 1.0 - (lag / (bandwidth + 1.0))
                        cov_lag = np.sum(w_t[lag:] * w_t[:-lag] * residuals[lag:] * residuals[:-lag])
                        gamma_sum += 2.0 * weight * cov_lag
                    var_hac = (gamma_0 + gamma_sum) / max(denom ** 2, 1e-9)
                    se_beta = math.sqrt(max(var_hac, 1e-12))

                t_stat = slope / max(se_beta, 1e-9)
                raw_p = round(cls._student_t_pvalue(t_stat, T - 2), 4)
                raw_p_list.append(raw_p)
            except Exception:
                raw_p_list.append(None)

        fdr_p_list = cls.benjamini_hochberg_correction(raw_p_list, q=q)

        mapping: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
        for idx, comb in enumerate(combinations):
            mapping[comb.combination_id] = (raw_p_list[idx], fdr_p_list[idx])

        return mapping

    # =========================================================================
    # 2. PREPROCESSING & TIMELINE ALIGNMENT
    # =========================================================================
    @classmethod
    def prepare_time_series(
        cls,
        df: pd.DataFrame,
        date_col: str,
        metric_col: str,
        granularity: Optional[DateGranularity] = None,
    ) -> Tuple[pd.DataFrame, DateGranularity, List[str]]:
        """
        Parses dates, handles duplicates via aggregation, aligns to calendar intervals,
        and marks duration-based partial periods.
        """
        warnings: List[str] = []
        clean_df = df[[date_col, metric_col]].copy()

        clean_df[date_col] = pd.to_datetime(clean_df[date_col], errors="coerce")
        clean_df[metric_col] = pd.to_numeric(clean_df[metric_col], errors="coerce")
        clean_df = clean_df.dropna(subset=[date_col, metric_col])

        if len(clean_df) < 3:
            return pd.DataFrame(), "month", ["Fewer than 3 valid non-null timestamped records."]

        min_d = clean_df[date_col].min()
        max_d = clean_df[date_col].max()
        span_days = (max_d - min_d).days

        if granularity is None:
            if span_days > 365 * 3:
                gran = "year"
            elif span_days > 180:
                gran = "month"
            elif span_days > 21:
                gran = "week"
            else:
                gran = "day"
        else:
            gran = granularity

        # Group and aggregate duplicates
        if gran == "year":
            clean_df["_period_key"] = clean_df[date_col].dt.to_period("Y")
            freq_str = "YS"
        elif gran == "quarter":
            clean_df["_period_key"] = clean_df[date_col].dt.to_period("Q")
            freq_str = "QS"
        elif gran == "month":
            clean_df["_period_key"] = clean_df[date_col].dt.to_period("M")
            freq_str = "MS"
        elif gran == "week":
            clean_df["_period_key"] = clean_df[date_col].dt.to_period("W-MON")
            freq_str = "W-MON"
        else:
            clean_df["_period_key"] = clean_df[date_col].dt.to_period("D")
            freq_str = "D"

        grouped = clean_df.groupby("_period_key").agg(
            metric_val=(metric_col, "sum" if any(k in metric_col.lower() for k in ("revenue", "sales", "amount", "total", "volume")) else "mean"),
            min_ts=(date_col, "min"),
            max_ts=(date_col, "max"),
            record_count=(metric_col, "count"),
        ).reset_index()

        # Resample onto uniform timeline without inserting artificial zero drops
        grouped["_timestamp"] = grouped["_period_key"].dt.to_timestamp()
        grouped = grouped.sort_values(by="_timestamp")

        # Evaluate duration-based period completeness (Safeguard #3)
        # We evaluate the span covered in the period rather than assuming every calendar day has a transaction.
        records: List[Dict[str, Any]] = []
        total_p = len(grouped)

        for idx, row in grouped.iterrows():
            p_key = row["_period_key"]
            val = float(row["metric_val"])
            min_t = row["min_ts"]
            max_t = row["max_ts"]

            is_partial = False
            completeness = 100.0

            # Only evaluate partial periods if input dataset has sub-period resolution (e.g. daily dates in monthly bins)
            has_subperiod_data = clean_df[date_col].dt.day.nunique() > 1
            if has_subperiod_data and gran == "month":
                year = p_key.year
                month = p_key.month
                total_month_days = calendar.monthrange(year, month)[1]
                # If first period or last period, check start/end day bounds
                if idx == 0:
                    covered_days = (min_t.replace(day=total_month_days) - min_t).days + 1
                    completeness = round((covered_days / total_month_days) * 100.0, 1)
                    if min_t.day > 7 and completeness < 75.0:
                        is_partial = True
                elif idx == total_p - 1:
                    covered_days = max_t.day
                    completeness = round((covered_days / total_month_days) * 100.0, 1)
                    if max_t.day < (total_month_days - 5) and completeness < 75.0:
                        is_partial = True
            elif has_subperiod_data and gran == "week":
                # For week, span in days between min and max timestamp
                covered_days = (max_t - min_t).days + 1
                completeness = round((covered_days / 7.0) * 100.0, 1)
                if (idx == 0 or idx == total_p - 1) and completeness < 50.0:
                    is_partial = True

            records.append({
                "period_label": str(p_key),
                "timestamp": row["_timestamp"].isoformat(),
                "value": val,
                "is_partial_period": bool(is_partial),
                "temporal_completeness_pct": float(completeness),
                "record_count": int(row["record_count"]),
            })

        result_df = pd.DataFrame(records)
        return result_df, gran, warnings

    # =========================================================================
    # 3. STATISTICAL TREND CLASSIFICATION & AUTOCORRELATION
    # =========================================================================
    @classmethod
    def analyze_trend(
        cls,
        series_df: pd.DataFrame,
        date_col: str,
        metric_col: str,
        granularity: DateGranularity,
        start_fact_idx: int = 1,
        p_value_fdr_adjusted: Optional[float] = None,
        total_hypotheses_screened: int = 1,
    ) -> Tuple[Optional[TrendAnalysis], List[QueryResultFact]]:
        """
        Executes OLS slope estimation, Durbin-Watson autocorrelation verification,
        Newey-West HAC standard error adjustment, Mann-Kendall monotonic ranking,
        strictly separated absolute vs conventional percentage change reporting,
        and Benjamini-Hochberg FDR control when multiple hypotheses are screened.
        """
        facts: List[QueryResultFact] = []
        fact_idx = start_fact_idx

        if len(series_df) < 3:
            return None, []

        y_vals = series_df["value"].to_numpy(dtype=float)
        T = len(y_vals)
        t_index = np.arange(1, T + 1, dtype=float)

        y_first = float(y_vals[0])
        y_last = float(y_vals[-1])
        y_max = float(np.max(y_vals))
        y_min = float(np.min(y_vals))
        y_range = y_max - y_min
        y_mean = float(np.mean(y_vals))
        y_std = float(np.std(y_vals)) if T > 1 else 0.0

        # Change Reporting Rules
        abs_change = round(y_last - y_first, 2)
        conv_growth_pct: Optional[float] = None
        range_norm_shift: Optional[float] = None

        if y_first > 0:
            conv_growth_pct = round(((y_last - y_first) / y_first) * 100.0, 1)
        else:
            # Baseline is zero or negative: use range-normalized shift (clearly labeled, never called growth)
            conv_growth_pct = None
            if y_range > 0:
                range_norm_shift = round(((y_last - y_first) / y_range) * 100.0, 1)
            else:
                range_norm_shift = 0.0

        # Constant Series Check
        if y_range == 0.0:
            analysis = TrendAnalysis(
                trend_id=f"trend_{uuid.uuid4().hex[:8]}",
                date_column=date_col,
                metric_column=metric_col,
                granularity=granularity,
                direction="stable",
                statistical_evidence="statistically_supported",
                business_magnitude="immaterial",
                p_value=1.0,
                p_value_fdr_adjusted=1.0,
                durbin_watson_stat=2.0,
                trend_strength_r2=0.0,
                absolute_change=0.0,
                formatted_absolute_change="0.00",
                conventional_growth_pct=0.0 if y_first > 0 else None,
                range_normalized_shift_pct=0.0,
                start_period=series_df["period_label"].iloc[0],
                end_period=series_df["period_label"].iloc[-1],
                start_value=y_first,
                end_value=y_last,
                peak_period=series_df["period_label"].iloc[0],
                peak_value=y_first,
                trough_period=series_df["period_label"].iloc[0],
                trough_value=y_first,
                explanation=f"Metric '{metric_col}' maintained an invariant constant value of {y_first:,.2f} across all {T} periods.",
            )
            return analysis, facts

        # OLS Linear Regression for all T >= 3
        t_bar = np.mean(t_index)
        denom = np.sum((t_index - t_bar) ** 2)
        slope = float(np.sum((t_index - t_bar) * (y_vals - y_mean)) / denom) if denom != 0 else 0.0
        intercept = float(y_mean - slope * t_bar)
        y_pred = intercept + slope * t_index
        residuals = y_vals - y_pred

        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((y_vals - y_mean) ** 2))
        r2 = round(max(0.0, min(1.0, 1.0 - (ss_res / max(ss_tot, 1e-9)))), 3)

        # Sample size sufficiency for hypothesis testing
        if T < 6:
            evidence: StatisticalEvidence = "insufficient_sample"
            p_val = None
            dw_stat = None
        else:
            # Durbin-Watson Statistic for Autocorrelation
            diff_res = np.diff(residuals)
            dw_stat = float(np.sum(diff_res ** 2) / max(ss_res, 1e-9))
            dw_stat = round(dw_stat, 2)

            # Newey-West HAC Standard Error Adjustment if Autocorrelated (DW < 1.2 or DW > 2.8)
            var_ols = (ss_res / max(T - 2, 1)) / max(denom, 1e-9)
            se_beta = math.sqrt(max(var_ols, 1e-12))

            if dw_stat < 1.2 or dw_stat > 2.8:
                # Bandwidth L = floor(0.75 * T^(1/3))
                bandwidth = max(1, int(0.75 * (T ** (1.0 / 3.0))))
                w_t = t_index - t_bar
                gamma_0 = np.sum((w_t ** 2) * (residuals ** 2))

                gamma_sum = 0.0
                for lag in range(1, bandwidth + 1):
                    weight = 1.0 - (lag / (bandwidth + 1.0))
                    cov_lag = np.sum(w_t[lag:] * w_t[:-lag] * residuals[lag:] * residuals[:-lag])
                    gamma_sum += 2.0 * weight * cov_lag

                var_hac = (gamma_0 + gamma_sum) / max(denom ** 2, 1e-9)
                se_beta = math.sqrt(max(var_hac, 1e-12))

            t_stat = slope / max(se_beta, 1e-9)
            p_val = round(cls._student_t_pvalue(t_stat, T - 2), 4)

            # Mann-Kendall Monotonic Rank Check
            s_stat = 0
            for i in range(T - 1):
                for j in range(i + 1, T):
                    s_stat += int(np.sign(y_vals[j] - y_vals[i]))

            mk_dir = "increasing" if s_stat > 0 else ("decreasing" if s_stat < 0 else "neutral")

            # Determine Statistical Evidence (Fix 1: Multiple testing safeguard)
            effective_p = p_value_fdr_adjusted if (p_value_fdr_adjusted is not None and total_hypotheses_screened > 1) else p_val

            if effective_p is not None and effective_p <= 0.05 and ((slope > 0 and mk_dir == "increasing") or (slope < 0 and mk_dir == "decreasing")):
                evidence = "statistically_supported"
            elif effective_p is not None and effective_p <= 0.15:
                evidence = "weak_evidence"
            else:
                evidence = "inconclusive"

        # Determine Trend Direction
        effect_size = abs(slope * T)
        effect_ratio = effect_size / max(abs(y_mean), 1e-6)

        if (evidence == "statistically_supported" and effect_ratio >= 0.05) or (
            T >= 3 and r2 >= 0.60 and ((slope > 0 and y_last > y_first) or (slope < 0 and y_last < y_first))
        ):
            direction: TrendDirection = "increasing" if slope > 0 else "decreasing"
        else:
            cv = y_std / max(abs(y_mean), 1e-6)
            if cv > 0.15:
                direction = "fluctuating"
            else:
                direction = "stable"

        # Determine Business Magnitude (Fix 2: historical mean absolute value denominator)
        mean_abs_val = float(np.mean(np.abs(y_vals)))
        if mean_abs_val > 1e-9:
            magnitude_ratio = abs(abs_change) / mean_abs_val
        else:
            magnitude_ratio = 0.0

        if magnitude_ratio >= 0.20:
            magnitude: BusinessMagnitude = "material"
        elif magnitude_ratio >= 0.05:
            magnitude = "moderate"
        else:
            magnitude = "immaterial"

        # Find Peak and Trough (excluding partial periods if reliable)
        clean_periods = series_df[~series_df["is_partial_period"]]
        if len(clean_periods) < 2:
            clean_periods = series_df

        peak_row = clean_periods.loc[clean_periods["value"].idxmax()]
        trough_row = clean_periods.loc[clean_periods["value"].idxmin()]

        peak_period = str(peak_row["period_label"])
        peak_val = round(float(peak_row["value"]), 2)
        trough_period = str(trough_row["period_label"])
        trough_val = round(float(trough_row["value"]), 2)

        start_p = str(series_df["period_label"].iloc[0])
        end_p = str(series_df["period_label"].iloc[-1])

        # Register Facts
        fid_trend = f"fact_{fact_idx}"
        change_desc = f"{conv_growth_pct:+.1f}%" if conv_growth_pct is not None else f"absolute change {abs_change:+,.2f}"
        facts.append(
            QueryResultFact(
                fact_id=fid_trend,
                category="trend",
                column_name=f"{date_col}_{metric_col}",
                metric_name="trend_classification",
                value=direction,
                formatted_statement=f"Metric '{metric_col}' shows a {direction} trend over '{date_col}' ({change_desc}, {T} periods, {granularity}).",
            )
        )
        fact_idx += 1

        fid_peak = f"fact_{fact_idx}"
        facts.append(
            QueryResultFact(
                fact_id=fid_peak,
                category="trend",
                column_name=f"{date_col}_{metric_col}",
                metric_name="peak_period",
                value=peak_val,
                formatted_statement=f"Peak period for '{metric_col}' occurred in {peak_period} with {peak_val:,.2f}.",
            )
        )
        fact_idx += 1

        # Build Interactive Plotly Line Chart
        chart = ChartConfig(
            chart_id=f"chart_trend_{uuid.uuid4().hex[:8]}",
            title=f"{metric_col.replace('_', ' ').title()} Trend over Time",
            chart_type="line",
            x_column=date_col,
            y_column=metric_col,
            plotly_data=[
                {
                    "x": [str(p) for p in series_df["period_label"]],
                    "y": [round(float(v), 2) for v in series_df["value"]],
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": metric_col,
                    "line": {"color": THEME_COLORS[0], "width": 2.5},
                    "marker": {"size": 6, "color": THEME_COLORS[0]},
                }
            ],
            plotly_layout={
                "title": {"text": f"{metric_col.replace('_', ' ').title()} Trend over {date_col.replace('_', ' ').title()}"},
                "xaxis": {"title": date_col.replace('_', ' ').title(), "automargin": True},
                "yaxis": {"title": metric_col.replace('_', ' ').title(), "automargin": True},
            },
        )

        # Formulate Explanation
        explanation_parts = [
            f"Observed {direction} movement in '{metric_col}' across {T} {granularity} periods ({start_p} to {end_p}).",
        ]
        if conv_growth_pct is not None:
            explanation_parts.append(f"Net change recorded at {conv_growth_pct:+.1f}% (from {y_first:,.2f} to {y_last:,.2f}, absolute delta: {abs_change:+,.2f}).")
        else:
            explanation_parts.append(f"Starting value was non-positive ({y_first:,.2f}); shifted by {abs_change:+,.2f} (range-normalized shift: {range_norm_shift:+.1f}% of historical span).")

        p_str = f"p={p_val:.4f}" if p_val is not None else "p=N/A"
        if p_value_fdr_adjusted is not None and total_hypotheses_screened > 1:
            p_str += f", p_FDR={p_value_fdr_adjusted:.4f}"
        explanation_parts.append(f"Statistical evidence: {evidence.replace('_', ' ')} ({p_str}, R²={r2:.2f}, business impact: {magnitude}).")
        explanation_parts.append(f"Highest period was {peak_period} ({peak_val:,.2f}); lowest period was {trough_period} ({trough_val:,.2f}).")

        analysis = TrendAnalysis(
            trend_id=f"trend_{uuid.uuid4().hex[:8]}",
            date_column=date_col,
            metric_column=metric_col,
            granularity=granularity,
            direction=direction,
            statistical_evidence=evidence,
            business_magnitude=magnitude,
            p_value=p_val,
            p_value_fdr_adjusted=p_value_fdr_adjusted,
            durbin_watson_stat=dw_stat,
            trend_strength_r2=r2,
            absolute_change=abs_change,
            formatted_absolute_change=f"{abs_change:+,.2f}",
            conventional_growth_pct=conv_growth_pct,
            range_normalized_shift_pct=range_norm_shift,
            start_period=start_p,
            end_period=end_p,
            start_value=round(y_first, 2),
            end_value=round(y_last, 2),
            peak_period=peak_period,
            peak_value=peak_val,
            trough_period=trough_period,
            trough_value=trough_val,
            data_points=[
                PeriodDataPoint(
                    period_label=str(r["period_label"]),
                    timestamp=str(r["timestamp"]),
                    value=round(float(r["value"]), 2),
                    formatted_value=f"{float(r['value']):,.2f}",
                    is_partial_period=bool(r["is_partial_period"]),
                    temporal_completeness_pct=float(r["temporal_completeness_pct"]),
                )
                for _, r in series_df.iterrows()
            ],
            chart=chart,
            explanation=" ".join(explanation_parts),
            referenced_fact_ids=[fid_trend, fid_peak],
        )

        return analysis, facts

    # =========================================================================
    # 4. ROBUST TEMPORAL ANOMALY DETECTION (ZERO-MAD FALLBACK)
    # =========================================================================
    @classmethod
    def detect_temporal_anomalies(
        cls,
        series_df: pd.DataFrame,
        date_col: str,
        metric_col: str,
        start_fact_idx: int = 1,
    ) -> Tuple[List[TemporalAnomaly], List[QueryResultFact]]:
        """
        Detects sudden spikes and drops on consecutive period differences using
        the Iglewicz-Hoaglin Modified Z-Score with an explicit two-stage Zero-MAD fallback.
        Enforces Safeguard #1: Do not multiply 0.6745 twice!
        """
        anomalies: List[TemporalAnomaly] = []
        facts: List[QueryResultFact] = []
        fact_idx = start_fact_idx

        y_vals = series_df["value"].to_numpy(dtype=float)
        T = len(y_vals)

        # Small sample safeguard
        if T < 5:
            return anomalies, facts

        periods = list(series_df["period_label"])
        y_range = float(np.max(y_vals) - np.min(y_vals))

        # First-order period differences
        diffs = np.diff(y_vals)  # length T - 1
        median_diff = float(np.median(diffs))
        abs_devs = np.abs(diffs - median_diff)
        mad = float(np.median(abs_devs))

        # Two-stage Zero-MAD fallback
        use_mad = False
        use_mean_ad = False
        use_step_check = False
        scale_est = 0.0

        if mad > 1e-9:
            use_mad = True
        else:
            # Stage 1: Mean Absolute Deviation about mean
            mean_diff = float(np.mean(diffs))
            mean_ad = float(np.mean(np.abs(diffs - mean_diff)))
            if mean_ad > 1e-9:
                use_mean_ad = True
                # Scale consistency factor sqrt(pi/2) approx 1.2533
                scale_est = 1.2533 * mean_ad
            else:
                # Stage 2: All differences are strictly identical (MeanAD == 0)
                use_step_check = True

        for i in range(len(diffs)):
            diff_val = float(diffs[i])
            curr_period = periods[i + 1]
            prev_val = float(y_vals[i])
            curr_val = float(y_vals[i + 1])

            # Conventional percentage delta only when prev_val > 0
            if prev_val > 0:
                delta_pct: Optional[float] = round(((curr_val - prev_val) / prev_val) * 100.0, 1)
            else:
                delta_pct = None

            is_anomaly = False
            anomaly_type: Literal["sudden_spike", "sudden_drop", "deterministic_step_anomaly"] = "sudden_spike"
            method_str = ""
            reason_str = ""
            score = 0.0

            if use_mad:
                # Standard Modified Z-Score: M_t = 0.67449 * |diff - median| / MAD
                score = (0.67449 * abs(diff_val - median_diff)) / mad
                method_str = "Modified Z-Score on Period Differences (MAD > 0)"
            elif use_mean_ad:
                # MeanAD scale fallback (Safeguard #1: scale_est already accounts for standard deviation)
                score = abs(diff_val - median_diff) / scale_est
                method_str = "MeanAD Robust Scale Fallback (Zero-MAD)"
            elif use_step_check:
                # Deterministic check against constant baseline difference
                step_dev = abs(diff_val - median_diff)
                if y_range > 0 and step_dev >= 0.20 * y_range:
                    is_anomaly = True
                    anomaly_type = "deterministic_step_anomaly"
                    method_str = "Deterministic Step Outlier (Identical Baseline Differences)"
                    reason_str = f"Isolated shift of {diff_val:+,.2f} from constant period difference ({median_diff:+,.2f})."

            if (use_mad and score >= 3.0) or (use_mean_ad and score >= 2.5):
                # Effect size check: must exceed 15% of historical range
                if y_range > 0 and abs(diff_val) >= 0.15 * y_range:
                    is_anomaly = True
                    anomaly_type = "sudden_spike" if diff_val > 0 else "sudden_drop"
                    pct_desc = f" ({delta_pct:+.1f}%)" if delta_pct is not None else ""
                    reason_str = (
                        f"Value shifted from {prev_val:,.2f} to {curr_val:,.2f}{pct_desc}, "
                        f"exceeding {score:.1f}x the robust scale dispersion."
                    )

            if is_anomaly:
                sev: Literal["critical", "warning", "info"] = "critical" if score >= 4.5 or (delta_pct and abs(delta_pct) >= 75) else "warning"

                fid = f"fact_{fact_idx}"
                facts.append(
                    QueryResultFact(
                        fact_id=fid,
                        category="temporal_anomaly",
                        column_name=f"{date_col}_{metric_col}",
                        metric_name=anomaly_type,
                        value=round(diff_val, 2),
                        formatted_statement=f"Detected {sev} {anomaly_type.replace('_', ' ')} in {curr_period}: {reason_str}",
                    )
                )
                fact_idx += 1

                anomalies.append(
                    TemporalAnomaly(
                        anomaly_id=f"tanomaly_{uuid.uuid4().hex[:8]}",
                        anomaly_type=anomaly_type,
                        severity=sev,
                        date_column=date_col,
                        metric_column=metric_col,
                        period_label=curr_period,
                        previous_value=round(prev_val, 2),
                        current_value=round(curr_val, 2),
                        delta_abs=round(diff_val, 2),
                        delta_pct=delta_pct,
                        detection_method=method_str,
                        detection_reason=reason_str,
                        referenced_fact_ids=[fid],
                    )
                )

        return anomalies, facts

    # =========================================================================
    # 5. RIGOROUS DETRENDED SEASONALITY VERIFICATION (ANOVA + KRUSKAL)
    # =========================================================================
    @classmethod
    def analyze_seasonality(
        cls,
        df: pd.DataFrame,
        date_col: str,
        metric_col: str,
        start_fact_idx: int = 1,
    ) -> Tuple[SeasonalityAnalysis, List[QueryResultFact]]:
        """
        Evaluates recurring cyclical patterns using One-Way ANOVA and Kruskal-Wallis
        performed strictly on detrended residuals across verified daily or monthly timelines.
        Enforces Safeguard #2: Mutually exclusive status states!
        """
        facts: List[QueryResultFact] = []
        fact_idx = start_fact_idx

        clean = df[[date_col, metric_col]].copy()
        clean[date_col] = pd.to_datetime(clean[date_col], errors="coerce")
        clean[metric_col] = pd.to_numeric(clean[metric_col], errors="coerce")
        clean = clean.dropna().sort_values(by=date_col)

        if len(clean) < 14:
            return (
                SeasonalityAnalysis(
                    is_detected=False,
                    status="insufficient_duration",
                    explanation="Dataset has insufficient historical duration (< 14 records) to test for recurring cyclical seasonality.",
                ),
                facts,
            )

        min_d = clean[date_col].min()
        max_d = clean[date_col].max()
        span_days = (max_d - min_d).days

        # Determine eligible cycle type
        # Day-of-week requires DAILY observations (span >= 28 days, >= 4 full weeks)
        is_daily_candidate = span_days >= 28 and len(clean) >= 28
        is_monthly_candidate = span_days >= 730  # >= 2 calendar years (24 months)

        if not is_daily_candidate and not is_monthly_candidate:
            return (
                SeasonalityAnalysis(
                    is_detected=False,
                    status="insufficient_duration",
                    explanation=f"Dataset span ({span_days} days) does not satisfy the minimum duration requirements: >= 4 weeks of daily records for day-of-week or >= 2 years for monthly seasonality.",
                ),
                facts,
            )

        cycle_type: Literal["day_of_week", "month_of_year"] = "day_of_week" if is_daily_candidate and span_days < 730 else "month_of_year"

        # Detrending: fit OLS trendline and calculate residuals
        t_seq = np.arange(len(clean), dtype=float)
        y_vals = clean[metric_col].to_numpy(dtype=float)
        t_mean = np.mean(t_seq)
        t_denom = np.sum((t_seq - t_mean) ** 2)
        slope = float(np.sum((t_seq - t_mean) * (y_vals - np.mean(y_vals))) / t_denom) if t_denom != 0 else 0.0
        intercept = float(np.mean(y_vals) - slope * t_mean)
        trendline = intercept + slope * t_seq
        residuals = y_vals - trendline
        clean["_residual"] = residuals

        if cycle_type == "day_of_week":
            clean["_group"] = clean[date_col].dt.dayofweek  # 0=Monday..6=Sunday
            group_labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            min_groups_populated = 5
        else:
            clean["_group"] = clean[date_col].dt.month  # 1..12
            group_labels = [calendar.month_name[m] for m in range(1, 13)]
            min_groups_populated = 8

        # Group detrended residuals
        grouped_residuals = [group["_residual"].values for _, group in clean.groupby("_group")]

        if len(grouped_residuals) < min_groups_populated or any(len(g) == 0 for g in grouped_residuals):
            return (
                SeasonalityAnalysis(
                    is_detected=False,
                    status="insufficient_duration",
                    cycle_type=cycle_type,
                    explanation=f"Insufficient populated cycle buckets to evaluate {cycle_type.replace('_', ' ')} seasonality.",
                ),
                facts,
            )

        # One-Way ANOVA on detrended residuals
        try:
            N_tot = len(clean)
            k_groups = len(grouped_residuals)
            grand_mean = float(np.mean(clean["_residual"]))
            ssb = sum(len(g) * ((float(np.mean(g)) - grand_mean) ** 2) for g in grouped_residuals)
            ssw = sum(sum((float(v) - float(np.mean(g))) ** 2 for v in g) for g in grouped_residuals)
            msb = ssb / max(k_groups - 1, 1)
            msw = ssw / max(N_tot - k_groups, 1)
            f_calc = float(msb / max(msw, 1e-12))
            f_stat = round(f_calc, 3)
            p_val_anova = round(cls._f_distribution_pvalue(f_calc, k_groups - 1, N_tot - k_groups), 4)
        except Exception:
            f_stat = None
            p_val_anova = None

        # Kruskal-Wallis Non-Parametric Check on detrended residuals
        try:
            N_tot = len(clean)
            clean_sorted = clean.copy()
            clean_sorted["_rank"] = clean_sorted["_residual"].rank(method="average")
            k_groups = len(grouped_residuals)
            h_sum = sum(
                (len(g) * ((clean_sorted.loc[g.index, "_rank"].mean()) ** 2))
                for _, g in clean_sorted.groupby("_group")
            )
            h_calc = (12.0 / (N_tot * (N_tot + 1))) * h_sum - 3.0 * (N_tot + 1)
            h_stat = round(float(max(0.0, h_calc)), 3)
            p_val_kruskal = round(cls._chi2_pvalue(h_calc, k_groups - 1), 4)
        except Exception:
            h_stat = None
            p_val_kruskal = None

        # Mutually exclusive status determination (Safeguard #2)
        if p_val_anova is not None and p_val_anova <= 0.05 and (p_val_kruskal is not None and p_val_kruskal <= 0.05):
            status: SeasonalityStatus = "statistically_supported"
            is_detected = True
        elif (p_val_anova is not None and p_val_anova <= 0.15) or (p_val_kruskal is not None and p_val_kruskal <= 0.15):
            status = "exploratory_pattern"
            is_detected = True
        else:
            status = "no_seasonality_detected"
            is_detected = False

        # Build Seasonal Pattern Breakdown
        overall_mean = float(clean[metric_col].mean())
        patterns: List[SeasonalPattern] = []

        summary_df = clean.groupby("_group").agg(
            avg_res=("_residual", "mean"),
            avg_raw=(metric_col, "mean"),
            occurrences=(metric_col, "count"),
        ).reset_index()

        peak_season: Optional[str] = None
        trough_season: Optional[str] = None

        if not summary_df.empty:
            summary_df = summary_df.sort_values(by="avg_res", ascending=False)
            top_grp = int(summary_df.iloc[0]["_group"])
            bot_grp = int(summary_df.iloc[-1]["_group"])
            peak_season = group_labels[top_grp if cycle_type == "day_of_week" else top_grp - 1]
            trough_season = group_labels[bot_grp if cycle_type == "day_of_week" else bot_grp - 1]

            for _, row in summary_df.iterrows():
                grp_idx = int(row["_group"])
                lbl = group_labels[grp_idx if cycle_type == "day_of_week" else grp_idx - 1]
                avg_res = float(row["avg_res"])
                raw_val = float(row["avg_raw"])
                delta_pct = round(((raw_val - overall_mean) / max(abs(overall_mean), 1e-6)) * 100.0, 1)

                patterns.append(
                    SeasonalPattern(
                        cycle_type=cycle_type,
                        period_name=lbl,
                        average_residual=round(avg_res, 2),
                        formatted_average=f"{raw_val:,.2f}",
                        delta_vs_overall_avg_pct=delta_pct,
                        sample_occurrences=int(row["occurrences"]),
                    )
                )

        chart = None
        if patterns:
            chart = ChartConfig(
                chart_id=f"chart_seas_{uuid.uuid4().hex[:8]}",
                title=f"Recurring {cycle_type.replace('_', ' ').title()} Pattern",
                chart_type="bar",
                x_column="Period",
                y_column="Delta vs Average (%)",
                plotly_data=[
                    {
                        "x": [p.period_name for p in patterns],
                        "y": [p.delta_vs_overall_avg_pct for p in patterns],
                        "type": "bar",
                        "marker": {
                            "color": [
                                THEME_COLORS[2] if i == 0 else (THEME_COLORS[3] if i == len(patterns) - 1 else THEME_COLORS[1])
                                for i in range(len(patterns))
                            ]
                        },
                    }
                ],
                plotly_layout={
                    "title": {"text": f"Seasonal Deviation across {cycle_type.replace('_', ' ').title()}"},
                    "xaxis": {"title": "Cycle Bucket", "automargin": True},
                    "yaxis": {"title": "% Deviation from Mean", "automargin": True},
                },
            )

        if is_detected:
            fid = f"fact_{fact_idx}"
            facts.append(
                QueryResultFact(
                    fact_id=fid,
                    category="seasonality",
                    column_name=f"{date_col}_{metric_col}",
                    metric_name=f"{cycle_type}_seasonality",
                    value=status,
                    formatted_statement=f"Observed {status.replace('_', ' ')} {cycle_type.replace('_', ' ')} seasonality (peak: {peak_season}, trough: {trough_season}, ANOVA p={p_val_anova}).",
                )
            )
            fact_idx += 1

        if status == "statistically_supported":
            expl = f"Statistically confirmed {cycle_type.replace('_', ' ')} seasonality on detrended residuals (ANOVA F={f_stat}, p={p_val_anova}; Kruskal p={p_val_kruskal}). Peak cyclical performance occurs in {peak_season}; lowest in {trough_season}."
        elif status == "exploratory_pattern":
            expl = f"Exploratory {cycle_type.replace('_', ' ')} pattern observed (ANOVA p={p_val_anova}). Shows higher averages in {peak_season}, but requires additional chronological cycles for statistical confirmation."
        else:
            expl = f"No statistically significant {cycle_type.replace('_', ' ')} seasonality detected (ANOVA p={p_val_anova if p_val_anova is not None else 'N/A'}; variance across cycle periods is consistent with random noise)."

        return (
            SeasonalityAnalysis(
                is_detected=is_detected,
                status=status,
                cycle_type=cycle_type,
                anova_f_stat=f_stat,
                anova_p_value=p_val_anova,
                kruskal_p_value=p_val_kruskal,
                peak_season=peak_season,
                trough_season=trough_season,
                patterns=patterns,
                chart=chart,
                explanation=expl,
                referenced_fact_ids=[f.fact_id for f in facts],
            ),
            facts,
        )
