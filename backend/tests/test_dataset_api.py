import io
import shutil
import tempfile
from pathlib import Path
import openpyxl
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.dataset_storage import DatasetStorageService, dataset_storage


@pytest.fixture(autouse=True)
def setup_test_storage(monkeypatch):
    """Isolate uploads directory during tests and clean up afterwards."""
    test_dir = tempfile.mkdtemp()
    test_storage = DatasetStorageService(upload_dir=test_dir)
    monkeypatch.setattr("app.services.dataset_storage.dataset_storage", test_storage)
    monkeypatch.setattr("app.api.routes.datasets.dataset_storage", test_storage)
    yield test_storage
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint_preserved(client):
    """Requirement 1: Preserve all working Phase 1 functionality."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "AutoAnalyst AI"


def test_root_endpoint_preserved(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "tagline" in data
    assert "brand" in data


def test_upload_csv_success(client, setup_test_storage):
    """Test standard CSV upload, profiling, preview, and safe serialization."""
    csv_content = (
        "Name,Age,Salary,Department\n"
        "Alice,28,75000.50,Engineering\n"
        "Bob,34,,Product\n"
        "Charlie,42,120000.0,Engineering\n"
        "Alice,28,75000.50,Engineering\n"  # duplicate row
    )
    files = {"file": ("test_employees.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/api/v1/datasets/upload", files=files)

    assert response.status_code == 201
    data = response.json()

    # Verify overview
    overview = data["overview"]
    assert len(overview["id"]) == 32  # 32 hex chars secure ID
    assert overview["filename"] == "test_employees.csv"
    assert overview["row_count"] == 4
    assert overview["column_count"] == 4
    assert overview["duplicate_rows"] == 1
    assert overview["duplicate_percentage"] == 25.0
    assert overview["missing_cells"] == 1  # Bob's salary is empty

    # Verify column profile
    cols = data["columns"]
    assert len(cols) == 4
    salary_col = next(c for c in cols if c["name"] == "Salary")
    assert salary_col["data_type"] == "float"
    assert salary_col["null_count"] == 1
    assert salary_col["null_percentage"] == 25.0
    assert salary_col["min"] == 75000.5
    assert salary_col["max"] == 120000.0

    # Verify preview
    preview = data["preview"]
    assert preview["total_rows"] == 4
    assert len(preview["rows"]) == 4
    assert preview["rows"][1]["Salary"] is None  # Safe JSON None, not NaN!

    # Verify security: no disk paths leaked
    raw_text = response.text
    assert "tmp_" not in raw_text
    assert setup_test_storage.upload_dir.as_posix() not in raw_text
    assert str(setup_test_storage.upload_dir) not in raw_text


def test_upload_xlsx_success(client):
    """Test XLSX upload with openpyxl engine."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"
    ws.append(["Region", "Revenue", "Units"])
    ws.append(["North", 15000, 120])
    ws.append(["South", 22000, 180])
    ws.append(["East", 18500, 150])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    files = {"file": ("quarterly_sales.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    response = client.post("/api/v1/datasets/upload", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["overview"]["row_count"] == 3
    assert data["overview"]["column_count"] == 3
    assert data["overview"]["filename"] == "quarterly_sales.xlsx"


def test_upload_xls_success(client):
    """Test XLS upload with xlrd engine."""
    import xlwt

    wb = xlwt.Workbook()
    ws = wb.add_sheet("Sheet1")
    ws.write(0, 0, "Product")
    ws.write(0, 1, "Price")
    ws.write(1, 0, "Laptop")
    ws.write(1, 1, 999.99)
    ws.write(2, 0, "Mouse")
    ws.write(2, 1, 29.50)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    files = {"file": ("legacy_data.xls", buf, "application/vnd.ms-excel")}
    response = client.post("/api/v1/datasets/upload", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["overview"]["row_count"] == 2
    assert data["overview"]["column_count"] == 2
    assert data["overview"]["filename"] == "legacy_data.xls"
    assert data["columns"][0]["name"] == "Product"
    assert data["columns"][1]["name"] == "Price"
    assert data["columns"][1]["data_type"] == "float"


def test_get_dataset_profile_endpoint(client):
    """Test dedicated GET /api/v1/datasets/{id}/profile endpoint."""
    csv_content = "Cat,Score\nA,10\nB,20\nA,30\n"
    files = {"file": ("scores.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files)
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["overview"]["id"]

    # Call dedicated /profile endpoint
    prof_res = client.get(f"/api/v1/datasets/{dataset_id}/profile")
    assert prof_res.status_code == 200
    prof_data = prof_res.json()
    assert "overview" in prof_data
    assert "columns" in prof_data
    assert prof_data["overview"]["id"] == dataset_id
    assert len(prof_data["columns"]) == 2
    score_col = next(c for c in prof_data["columns"] if c["name"] == "Score")
    assert score_col["mean"] == 20.0


def test_dataset_persistence_across_restart(client, setup_test_storage, monkeypatch):
    """Verify that dataset metadata and files persist after storage restart."""
    csv_content = "ID,Value\n1,Alpha\n2,Beta\n3,Gamma\n"
    files = {"file": ("persistent.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files)
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["overview"]["id"]

    # Simulate backend restart by instantiating a completely new DatasetStorageService
    # pointing to the exact same storage directory
    restarted_storage = DatasetStorageService(upload_dir=str(setup_test_storage.upload_dir))
    monkeypatch.setattr("app.services.dataset_storage.dataset_storage", restarted_storage)
    monkeypatch.setattr("app.api.routes.datasets.dataset_storage", restarted_storage)

    # 1. Verify dataset is listed after restart
    list_res = client.get("/api/v1/datasets")
    assert list_res.status_code == 200
    ids = [d["id"] for d in list_res.json()["datasets"]]
    assert dataset_id in ids

    # 2. Verify full dataset details and profile persist
    get_res = client.get(f"/api/v1/datasets/{dataset_id}")
    assert get_res.status_code == 200
    assert get_res.json()["overview"]["filename"] == "persistent.csv"
    assert len(get_res.json()["columns"]) == 2

    # 3. Verify underlying file can still be parsed for preview pagination
    prev_res = client.get(f"/api/v1/datasets/{dataset_id}/preview?limit=2&offset=1")
    assert prev_res.status_code == 200
    prev_data = prev_res.json()
    assert prev_data["preview_rows_count"] == 2
    assert prev_data["rows"][0]["ID"] == 2
    assert prev_data["rows"][1]["ID"] == 3


def test_upload_invalid_file_type(client):
    """Test rejection of non-spreadsheet extensions."""
    files = {"file": ("malicious.exe", io.BytesIO(b"MZ..."), "application/octet-stream")}
    response = client.post("/api/v1/datasets/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_upload_empty_file_zero_bytes(client):
    """Test rejection of 0-byte file."""
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    response = client.post("/api/v1/datasets/upload", files=files)
    assert response.status_code == 400
    assert "empty (0 bytes)" in response.json()["detail"]


def test_upload_empty_data_header_only(client):
    """Test rejection of header-only CSV with no rows."""
    files = {"file": ("header_only.csv", io.BytesIO(b"Col1,Col2\n"), "text/csv")}
    response = client.post("/api/v1/datasets/upload", files=files)
    assert response.status_code == 400
    assert "contains no data" in response.json()["detail"]


def test_upload_cleanup_on_failure(client, setup_test_storage):
    """Requirement 4: Verify partially uploaded files are cleaned up if parsing fails."""
    # Corrupt CSV that triggers parse failure or invalid binary
    files = {"file": ("corrupt.csv", io.BytesIO(b"\x00\x01\x02\x03\x04\xff\xfe"), "text/csv")}
    response = client.post("/api/v1/datasets/upload", files=files)
    assert response.status_code in (400, 500)

    # Assert no temporary files remained in the upload directory
    remaining_files = list(setup_test_storage.upload_dir.glob("tmp_*"))
    assert len(remaining_files) == 0


def test_column_limit_enforcement(client, monkeypatch):
    """Requirement 3: Enforce configurable column limit."""
    monkeypatch.setattr(settings, "MAX_DATASET_COLUMNS", 5)
    # Generate CSV with 8 columns
    header = ",".join([f"Col{i}" for i in range(8)]) + "\n"
    row = ",".join([str(i) for i in range(8)]) + "\n"
    csv_data = (header + row).encode("utf-8")

    files = {"file": ("wide.csv", io.BytesIO(csv_data), "text/csv")}
    response = client.post("/api/v1/datasets/upload", files=files)
    assert response.status_code == 400
    assert "exceeds the maximum limit of 5" in response.json()["detail"]


def test_row_limit_enforcement(client, monkeypatch):
    """Requirement 3: Enforce configurable row limit."""
    monkeypatch.setattr(settings, "MAX_DATASET_ROWS", 10)
    # Generate CSV with 15 rows
    lines = ["ColA,ColB"] + [f"{i},val" for i in range(15)]
    csv_data = "\n".join(lines).encode("utf-8")

    files = {"file": ("long.csv", io.BytesIO(csv_data), "text/csv")}
    response = client.post("/api/v1/datasets/upload", files=files)
    assert response.status_code == 400
    assert "exceeds the maximum limit of 10" in response.json()["detail"]


def test_list_and_delete_datasets(client):
    """Test listing datasets, fetching details, preview pagination, and deletion."""
    csv_content = "X,Y\n1,10\n2,20\n3,30\n4,40\n5,50\n"
    files = {"file": ("coords.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files)
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["overview"]["id"]

    # 1. List datasets
    list_res = client.get("/api/v1/datasets")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total_datasets"] == 1
    assert list_data["total_rows_all"] == 5
    assert list_data["datasets"][0]["id"] == dataset_id

    # 2. Get specific dataset
    get_res = client.get(f"/api/v1/datasets/{dataset_id}")
    assert get_res.status_code == 200
    assert get_res.json()["overview"]["id"] == dataset_id

    # 3. Paginated preview
    preview_res = client.get(f"/api/v1/datasets/{dataset_id}/preview?limit=2&offset=2")
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["preview_rows_count"] == 2
    assert preview_data["rows"][0]["X"] == 3
    assert preview_data["rows"][1]["X"] == 4

    # 4. Delete dataset
    del_res = client.delete(f"/api/v1/datasets/{dataset_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 5. Verify 404 after deletion
    assert client.get(f"/api/v1/datasets/{dataset_id}").status_code == 404
