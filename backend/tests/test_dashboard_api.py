import io
import shutil
import tempfile
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.dashboard import CustomChartRequest, FilterDashboardRequest, FilterRule
from app.services.dashboard_service import dashboard_service
from app.services.dataset_storage import DatasetStorageService


@pytest.fixture(autouse=True)
def setup_test_storage(monkeypatch):
    test_dir = tempfile.mkdtemp()
    test_storage = DatasetStorageService(upload_dir=test_dir)
    monkeypatch.setattr("app.services.dataset_storage.dataset_storage", test_storage)
    monkeypatch.setattr("app.api.routes.datasets.dataset_storage", test_storage)
    monkeypatch.setattr("app.api.routes.dashboard.dataset_storage", test_storage)
    yield test_storage
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_dataset(client):
    csv_content = (
        "Date,Region,Product,Sales,Units,Discount\n"
        "2025-01-01,North,Widget,100.0,5,0.0\n"
        "2025-01-02,South,Gadget,250.0,10,0.1\n"
        "2025-01-03,North,Widget,150.0,6,0.05\n"
        "2025-01-04,East,Gadget,300.0,12,0.0\n"
        "2025-01-05,West,Doohickey,80.0,,0.0\n"  # missing Units
        "2025-01-06,North,Doohickey,120.0,4,0.0\n"
    )
    files = {"file": ("test_sales.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/v1/datasets/upload", files=files)
    assert res.status_code == 201
    return res.json()["overview"]["id"]


# 1. Dashboard KPI calculations
def test_dashboard_kpis(client, sample_dataset):
    res = client.get(f"/api/v1/datasets/{sample_dataset}/dashboard?selected_column=Sales")
    assert res.status_code == 200
    data = res.json()
    kpis = data["kpis"]
    assert kpis["total_rows"] == 6
    assert kpis["total_columns"] == 6
    assert kpis["missing_cells"] == 1
    assert kpis["data_completeness"] > 95.0
    assert kpis["selected_column"] == "Sales"
    assert kpis["selected_column_stats"]["sum"] == 1000.0
    assert kpis["selected_column_stats"]["average"] == round(1000.0 / 6, 2)
    assert kpis["selected_column_stats"]["minimum"] == 80.0
    assert kpis["selected_column_stats"]["maximum"] == 300.0


# 2. Chart recommendation for numeric columns (histogram / box plot)
def test_chart_recommendation_numeric(client, sample_dataset):
    res = client.get(f"/api/v1/datasets/{sample_dataset}/chart-recommendations")
    assert res.status_code == 200
    charts = res.json()
    types = [c["chart_type"] for c in charts]
    assert "histogram" in types or "box" in types


# 3. Chart recommendation for categorical columns (bar / pie)
def test_chart_recommendation_categorical(client, sample_dataset):
    res = client.get(f"/api/v1/datasets/{sample_dataset}/chart-recommendations")
    assert res.status_code == 200
    charts = res.json()
    types = [c["chart_type"] for c in charts]
    assert "bar" in types or "pie" in types


# 4. Datetime trend chart recommendations (line chart)
def test_chart_recommendation_datetime_trend(client, sample_dataset):
    res = client.get(f"/api/v1/datasets/{sample_dataset}/chart-recommendations")
    assert res.status_code == 200
    charts = res.json()
    line_charts = [c for c in charts if c["chart_type"] == "line"]
    assert len(line_charts) > 0
    assert line_charts[0]["x_column"] == "Date"


# 5. Aggregation calculations (Sum, Avg, Count, Min, Max)
def test_custom_chart_aggregations(client, sample_dataset):
    for agg in ["sum", "avg", "min", "max", "count"]:
        req = {
            "chart_type": "bar",
            "x_column": "Region",
            "y_column": "Sales",
            "aggregation": agg,
        }
        res = client.post(f"/api/v1/datasets/{sample_dataset}/charts/generate", json=req)
        assert res.status_code == 200
        data = res.json()
        assert len(data["plotly_data"]) > 0
        assert data["plotly_data"][0]["type"] == "bar"


# 6. Invalid column rejection
def test_invalid_column_rejection(client, sample_dataset):
    req = {
        "chart_type": "bar",
        "x_column": "NonExistentColumn",
        "y_column": "Sales",
        "aggregation": "sum",
    }
    res = client.post(f"/api/v1/datasets/{sample_dataset}/charts/generate", json=req)
    assert res.status_code == 400
    assert "does not exist in dataset" in res.json()["detail"]


# 7. Invalid chart type rejection
def test_invalid_chart_type_rejection(client, sample_dataset):
    req = {
        "chart_type": "3d_surface_unknown",
        "x_column": "Region",
    }
    res = client.post(f"/api/v1/datasets/{sample_dataset}/charts/generate", json=req)
    assert res.status_code == 400
    assert "Invalid chart type" in res.json()["detail"]


# 8. Invalid aggregation rejection
def test_invalid_aggregation_rejection(client, sample_dataset):
    req = {
        "chart_type": "bar",
        "x_column": "Region",
        "y_column": "Sales",
        "aggregation": "standard_deviation_invalid",
    }
    res = client.post(f"/api/v1/datasets/{sample_dataset}/charts/generate", json=req)
    assert res.status_code == 400
    assert "Invalid aggregation" in res.json()["detail"]


# 9. Categorical filters
def test_categorical_filter(client, sample_dataset):
    req = {
        "filters": [
            {
                "column": "Region",
                "filter_type": "categorical",
                "selected_values": ["North"],
            }
        ]
    }
    res = client.post(f"/api/v1/datasets/{sample_dataset}/dashboard/filter", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["is_filtered"] is True
    assert data["filtered_row_count"] == 3  # North appears 3 times
    assert data["total_row_count"] == 6


# 10. Numeric range filters
def test_numeric_range_filter(client, sample_dataset):
    req = {
        "filters": [
            {
                "column": "Sales",
                "filter_type": "numeric_range",
                "min_val": 150.0,
                "max_val": 300.0,
            }
        ]
    }
    res = client.post(f"/api/v1/datasets/{sample_dataset}/dashboard/filter", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["filtered_row_count"] == 3  # 150, 250, 300


# 11. Empty dataset handling
def test_empty_dataset_kpis_handling():
    empty_df = pd.DataFrame(columns=["A", "B"])
    kpis = dashboard_service.calculate_kpis(empty_df)
    assert kpis.total_rows == 0
    assert kpis.total_columns == 2
    assert kpis.missing_cells == 0
    assert kpis.data_completeness == 100.0


# 12. Missing-value handling
def test_missing_value_handling_in_charts(client, sample_dataset):
    # Units column has a missing value
    req = {
        "chart_type": "histogram",
        "x_column": "Units",
    }
    res = client.post(f"/api/v1/datasets/{sample_dataset}/charts/generate", json=req)
    assert res.status_code == 200
    data = res.json()
    assert len(data["plotly_data"][0]["x"]) == 5  # 5 non-null values, didn't crash on NaN!


# 13. Invalid dataset ID handling
def test_invalid_dataset_id_handling(client):
    res = client.get("/api/v1/datasets/non_existent_id_9999/dashboard")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]


# Extra: Category drilldown test
def test_category_drilldown(client, sample_dataset):
    req = {
        "category_column": "Region",
        "category_value": "North",
        "limit": 10,
        "offset": 0,
    }
    res = client.post(f"/api/v1/datasets/{sample_dataset}/dashboard/drilldown", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["total_matching_rows"] == 3
    assert len(data["sample_records"]) == 3
    assert data["summary_stats"]["numeric_metrics"]["Sales"]["sum"] == 370.0

