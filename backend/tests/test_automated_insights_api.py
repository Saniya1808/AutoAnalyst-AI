import io
import json
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.dataset_storage import dataset_storage

client = TestClient(app)


def upload_sample_dataset(csv_content: str, filename: str = "test_insights.csv") -> str:
    """Helper to upload a CSV dataset and return dataset_id."""
    file_bytes = csv_content.encode("utf-8")
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": (filename, io.BytesIO(file_bytes), "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()["overview"]["id"]


def test_automated_insights_endpoint_generation_and_caching():
    """Test GET /api/v1/datasets/{id}/insights generates insights and caches them."""
    csv_data = (
        "department,salary,bonus,employee_id\n"
        "Engineering,120000,15000,101\n"
        "Engineering,130000,18000,102\n"
        "Engineering,140000,20000,103\n"
        "Sales,90000,25000,104\n"
        "Sales,95000,28000,105\n"
        "Sales,85000,22000,106\n"
        "Marketing,75000,10000,107\n"
        "Marketing,80000,12000,108\n"
        "Marketing,70000,9000,109\n"
        "Support,50000,5000,110\n"
        "Support,52000,5500,111\n"
        "Support,48000,4500,112\n"
    )
    ds_id = upload_sample_dataset(csv_data, "dept_salaries.csv")

    # 1. First fetch - newly computed
    res = client.get(f"/api/v1/datasets/{ds_id}/insights")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["dataset_id"] == ds_id
    assert data["health_score"] >= 0
    assert len(data["key_findings"]) >= 1
    assert len(data["grounded_facts"]) >= 1
    assert data["is_cached"] is False

    # Check best and worst analysis
    assert len(data["best_worst_analyses"]) >= 1
    bw = data["best_worst_analyses"][0]
    assert bw["dimension_column"] == "department"
    assert bw["best_performer"]["category_name"] == "Engineering"
    assert bw["worst_performer"]["category_name"] == "Support"
    assert bw["chart"] is not None

    # Check recommendations
    assert len(data["recommendations"]) >= 1

    # Check identifier exclusion (employee_id should not be the metric column)
    assert bw["metric_column"] != "employee_id"

    # 2. Second fetch - should be cached
    res2 = client.get(f"/api/v1/datasets/{ds_id}/insights")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_cached"] is True

    # 3. Force refresh - should bypass cache
    res_refresh = client.post(f"/api/v1/datasets/{ds_id}/insights/refresh")
    assert res_refresh.status_code == 200
    data_refresh = res_refresh.json()
    assert data_refresh["is_cached"] is False


def test_broad_query_important_findings():
    """Test natural language: 'What are the most important findings?'"""
    csv_data = (
        "region,sales,satisfaction\n"
        "North,500,4.5\n"
        "South,200,3.2\n"
        "East,800,4.8\n"
        "West,300,3.9\n"
    )
    ds_id = upload_sample_dataset(csv_data, "regional_sales.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "What are the most important findings?", "include_chart": False},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["primary_metric"] is not None
    assert "Discovered Insights" in data["primary_metric"]["label"]
    assert len(data["tabular_data"]) >= 1
    assert "Finding" in data["tabular_data"][0]
    assert len(data["grounded_facts"]) >= 1


def test_broad_query_best_and_worst_categories():
    """Test natural language: 'Which categories perform best and worst?'"""
    csv_data = (
        "segment,profit\n"
        "Enterprise,10000\n"
        "Enterprise,12000\n"
        "Mid-Market,5000\n"
        "Mid-Market,6000\n"
        "Small-Business,1000\n"
        "Small-Business,1200\n"
    )
    ds_id = upload_sample_dataset(csv_data, "segments_profit.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Which categories perform best and worst?", "include_chart": True},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["primary_metric"] is not None
    assert "Enterprise" in data["primary_metric"]["label"]
    assert len(data["tabular_data"]) >= 3
    assert "Rank" in data["tabular_data"][0]
    assert data["chart"] is not None
    assert "Best performer is 'Enterprise'" in data["direct_answer"] or "Enterprise" in data["direct_answer"]


def test_broad_query_unusual_patterns_and_anomalies():
    """Test natural language: 'Are there unusual patterns?' with IQR outliers."""
    csv_data = (
        "sensor_id,temperature\n"
        "1,20.0\n"
        "2,21.0\n"
        "3,20.5\n"
        "4,22.0\n"
        "5,21.5\n"
        "6,19.8\n"
        "7,20.2\n"
        "8,99.9\n"  # Extreme outlier!
    )
    ds_id = upload_sample_dataset(csv_data, "temp_sensors.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Are there unusual patterns?", "include_chart": False},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["primary_metric"] is not None
    assert "Anomalies" in data["primary_metric"]["label"]
    assert len(data["tabular_data"]) >= 1
    assert any("temperature" in row["Column"].lower() for row in data["tabular_data"])
    assert any("outlier" in row["Pattern Type"].lower() for row in data["tabular_data"])


def test_broad_query_actionable_recommendations():
    """Test natural language: 'What actions would you recommend based on the data?'"""
    csv_data = (
        "channel,conversions,spend\n"
        "Organic,500,100\n"
        "Paid Search,300,5000\n"
        "Social,50,2000\n"
    )
    ds_id = upload_sample_dataset(csv_data, "marketing_roi.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "What actions would you recommend based on the data?", "include_chart": False},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["primary_metric"] is not None
    assert "Recommendations" in data["primary_metric"]["label"]
    assert len(data["tabular_data"]) >= 1
    assert "Recommended Action" in data["tabular_data"][0]
    assert "Classification" in data["tabular_data"][0]


def test_broad_query_data_quality_issues():
    """Test natural language: 'What are the most important data-quality issues?'"""
    csv_data = (
        "user_id,email,phone\n"
        "1,,123456\n"
        "2,,654321\n"
        "3,,112233\n"
        "4,,445566\n"
        "5,test@example.com,778899\n"
    )
    ds_id = upload_sample_dataset(csv_data, "users_incomplete.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "What are the most important data-quality issues?", "include_chart": False},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["primary_metric"] is not None
    assert "Data Health" in data["primary_metric"]["label"]
    assert len(data["tabular_data"]) >= 1


def test_pure_categorical_dataset_insights():
    """Test that pure categorical datasets without numeric metrics do not crash and generate frequency benchmarks."""
    csv_data = (
        "company_name,country,industry\n"
        "Infosys,India,IT Services\n"
        "TCS,India,IT Services\n"
        "Wipro,India,IT Services\n"
        "Accenture,Ireland,Consulting\n"
        "Capgemini,France,Consulting\n"
    )
    ds_id = upload_sample_dataset(csv_data, "pure_cat.csv")

    res = client.get(f"/api/v1/datasets/{ds_id}/insights")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["health_score"] >= 50
    assert len(data["best_worst_analyses"]) >= 1
    # Frequency benchmarks
    bw = data["best_worst_analyses"][0]
    assert bw["aggregation"] == "count"
    assert bw["best_performer"]["category_name"] in ("India", "IT Services")


def test_small_sample_exploratory_flag():
    """Verify that categories with n < 5 are flagged exploratory."""
    csv_data = (
        "tier,score\n"
        "Gold,95\n"
        "Gold,92\n"
        "Gold,98\n"
        "Gold,90\n"
        "Gold,96\n"  # n = 5 (reliable)
        "Silver,70\n"
        "Silver,72\n"  # n = 2 (exploratory)
    )
    ds_id = upload_sample_dataset(csv_data, "sample_sizes.csv")

    res = client.get(f"/api/v1/datasets/{ds_id}/insights")
    assert res.status_code == 200, res.text
    data = res.json()

    bw = data["best_worst_analyses"][0]
    gold = next(p for p in bw["ranked_performers"] if p["category_name"] == "Gold")
    silver = next(p for p in bw["ranked_performers"] if p["category_name"] == "Silver")

    assert gold["is_statistically_reliable"] is True
    assert silver["is_statistically_reliable"] is False


def test_broad_query_best_and_worst_categories_on_titanic():
    """Regression test for Issue 1: 'Which categories perform best and worst?' on Titanic."""
    csv_data = (
        "PassengerId,Survived,Pclass,Name,Sex,Age,Fare\n"
        "1,0,3,Braund Mr. Owen Harris,male,22,7.25\n"
        "2,1,1,Cumings Mrs. John Bradley,female,38,71.28\n"
        "3,1,3,Heikkinen Miss. Laina,female,26,7.92\n"
        "4,1,1,Futrelle Mrs. Jacques Heath,female,35,53.10\n"
        "5,0,3,Allen Mr. William Henry,male,35,8.05\n"
        "6,0,3,Moran Mr. James,male,,8.45\n"
    )
    ds_id = upload_sample_dataset(csv_data, "titanic_regression.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Which categories perform best and worst?", "include_chart": True},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["primary_metric"] is not None
    assert "female" in data["primary_metric"]["label"].lower() or "sex" in data["primary_metric"]["label"].lower()
    assert len(data["tabular_data"]) >= 2
    assert any("female" in row.get("Sex", "").lower() for row in data["tabular_data"])
    assert any("male" in row.get("Sex", "").lower() for row in data["tabular_data"])
    assert data["chart"] is not None


def test_automated_insights_findings_count_matches_bullets():
    """Regression test for Issue 2: Reported findings count must match the displayed bullet points."""
    csv_data = (
        "PassengerId,Survived,Pclass,Name,Sex,Age,Fare,Cabin\n"
        "1,0,3,Braund Mr. Owen Harris,male,22,7.25,\n"
        "2,1,1,Cumings Mrs. John Bradley,female,38,71.28,C85\n"
        "3,1,3,Heikkinen Miss. Laina,female,26,7.92,\n"
        "4,1,1,Futrelle Mrs. Jacques Heath,female,35,53.10,C123\n"
        "5,0,3,Allen Mr. William Henry,male,35,8.05,\n"
        "6,0,3,Moran Mr. James,male,,8.45,\n"
        "7,0,1,McCarthy Mr. Timothy J,male,54,51.86,E46\n"
        "8,0,3,Palsson Master. Gosta Leonard,male,2,21.07,\n"
    )
    ds_id = upload_sample_dataset(csv_data, "titanic_count_align.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "What are the most important findings?", "include_chart": False},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    direct_ans = data["direct_answer"]
    import re
    match = re.search(r"Discovered (\d+) automated insights", direct_ans)
    assert match is not None, f"Expected count pattern in direct_answer: {direct_ans}"

    reported_count = int(match.group(1))
    bullet_lines = [line for line in direct_ans.split("\n") if line.strip().startswith("- ")]
    assert reported_count == len(bullet_lines), (
        f"Reported {reported_count} insights but found {len(bullet_lines)} bullet items in: {direct_ans}"
    )


def test_fallback_when_ranked_performers_missing_or_duplicate():
    """Verify safe fallback in analytical executor when ranked_performers is None or has duplicate categories."""
    from app.models.ask_data import QueryPlan
    from app.services.ai.analytical_executor import AnalyticalExecutor
    import pandas as pd

    df = pd.DataFrame({"category": ["Alpha", "Alpha", "Alpha"], "value": [10.0, 10.0, 10.0]})
    plan = QueryPlan(
        plan_id="test_plan_bw_fallback",
        intent="best_worst_performers",
        operation="benchmark_performers",
    )
    result = AnalyticalExecutor.execute_plan(df=df, plan=plan, dataset_id="test_ds")
    assert result.success is True
    # Since only 1 category exists, it either returns graceful note or single deduplicated row
    assert len(result.tabular_data) <= 1

