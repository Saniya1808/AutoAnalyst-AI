import io
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.dataset_storage import DatasetStorageService


@pytest.fixture
def test_storage(monkeypatch):
    """Isolate uploads directory during tests."""
    test_dir = tempfile.mkdtemp()
    storage = DatasetStorageService(upload_dir=test_dir)
    monkeypatch.setattr("app.services.dataset_storage.dataset_storage", storage)
    monkeypatch.setattr("app.api.routes.datasets.dataset_storage", storage)
    monkeypatch.setattr("app.api.routes.reports.dataset_storage", storage)
    monkeypatch.setattr("app.api.routes.dashboard.dataset_storage", storage)
    monkeypatch.setattr("app.api.routes.automated_insights.dataset_storage", storage)
    monkeypatch.setattr("app.api.routes.ask_data.dataset_storage", storage)
    monkeypatch.setattr("app.api.routes.cleaning.dataset_storage", storage)
    monkeypatch.setattr("app.api.routes.ai_understanding.dataset_storage", storage)
    monkeypatch.setattr("app.services.reports.report_assembly_service.dataset_storage", storage)
    monkeypatch.setattr("app.services.ai.insights_synthesizer.dataset_storage", storage)
    monkeypatch.setattr("app.services.cleaning_service.dataset_storage", storage)
    yield storage
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(app)


def _upload_csv(client, session_id=None, filename="test_sales.csv"):
    csv_data = "Date,Product,Revenue,Units\n2024-01-01,Widget,100,5\n2024-01-02,Gadget,200,8\n"
    files = {"file": (filename, io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    headers = {"X-Session-ID": session_id} if session_id else {}
    resp = client.post("/api/v1/datasets/upload", files=files, headers=headers)
    assert resp.status_code == 201
    return resp.json()["overview"]["id"]


def test_session_isolation_list(client, test_storage):
    """Session A only sees its own datasets; Session B does not see Session A's."""
    id_a = _upload_csv(client, session_id="sess_Alpha", filename="alpha_sales.csv")
    id_b = _upload_csv(client, session_id="sess_Beta", filename="beta_sales.csv")

    # Alpha lists datasets
    resp_a = client.get("/api/v1/datasets", headers={"X-Session-ID": "sess_Alpha"})
    assert resp_a.status_code == 200
    ids_seen_by_a = [d["id"] for d in resp_a.json()["datasets"]]
    assert id_a in ids_seen_by_a
    assert id_b not in ids_seen_by_a

    # Beta lists datasets
    resp_b = client.get("/api/v1/datasets", headers={"X-Session-ID": "sess_Beta"})
    assert resp_b.status_code == 200
    ids_seen_by_b = [d["id"] for d in resp_b.json()["datasets"]]
    assert id_b in ids_seen_by_b
    assert id_a not in ids_seen_by_b


def test_session_isolation_get_and_preview(client, test_storage):
    """Session B cannot get or preview Session A's dataset."""
    id_a = _upload_csv(client, session_id="sess_Alpha")

    # Session A can get and preview
    resp_get_a = client.get(f"/api/v1/datasets/{id_a}", headers={"X-Session-ID": "sess_Alpha"})
    assert resp_get_a.status_code == 200

    resp_prev_a = client.get(f"/api/v1/datasets/{id_a}/preview", headers={"X-Session-ID": "sess_Alpha"})
    assert resp_prev_a.status_code == 200

    # Session B cannot get or preview
    resp_get_b = client.get(f"/api/v1/datasets/{id_a}", headers={"X-Session-ID": "sess_Beta"})
    assert resp_get_b.status_code == 404

    resp_prev_b = client.get(f"/api/v1/datasets/{id_a}/preview", headers={"X-Session-ID": "sess_Beta"})
    assert resp_prev_b.status_code == 404

    # Anonymous caller without session header cannot access
    resp_anon = client.get(f"/api/v1/datasets/{id_a}")
    assert resp_anon.status_code == 404


def test_session_isolation_delete(client, test_storage):
    """Session B cannot delete Session A's dataset."""
    id_a = _upload_csv(client, session_id="sess_Alpha")

    # Session B tries to delete Session A's dataset
    del_resp_b = client.delete(f"/api/v1/datasets/{id_a}", headers={"X-Session-ID": "sess_Beta"})
    assert del_resp_b.status_code == 404

    # Dataset still exists for Session A
    get_resp_a = client.get(f"/api/v1/datasets/{id_a}", headers={"X-Session-ID": "sess_Alpha"})
    assert get_resp_a.status_code == 200

    # Session A deletes its own dataset
    del_resp_a = client.delete(f"/api/v1/datasets/{id_a}", headers={"X-Session-ID": "sess_Alpha"})
    assert del_resp_a.status_code == 200


def test_public_sample_dataset_protection(client, test_storage):
    """Public sample datasets are readable by all sessions, but cannot be deleted."""
    # Create sample dataset in test storage
    id_sample = _upload_csv(client, session_id=None, filename="sample_superstore.csv")
    sample_detail = test_storage.get_dataset(id_sample)
    sample_detail.overview.is_sample = True

    # Both Session A and Session B can see and read it
    resp_a = client.get(f"/api/v1/datasets/{id_sample}", headers={"X-Session-ID": "sess_Alpha"})
    assert resp_a.status_code == 200

    resp_b = client.get(f"/api/v1/datasets/{id_sample}", headers={"X-Session-ID": "sess_Beta"})
    assert resp_b.status_code == 200

    # Attempting to delete returns 403 Forbidden
    del_resp = client.delete(f"/api/v1/datasets/{id_sample}", headers={"X-Session-ID": "sess_Alpha"})
    assert del_resp.status_code == 403
    assert "Sample datasets are protected" in del_resp.json()["detail"]


def test_session_isolation_reports_and_exports(client, test_storage):
    """Session A can generate reports and export PDF/Excel. Session B & anonymous are blocked (404)."""
    id_a = _upload_csv(client, session_id="sess_Alpha", filename="alpha_finance.csv")

    # 1. Session A (Owner) generates report preview
    rep_res_a = client.post(f"/api/v1/datasets/{id_a}/reports/generate", json={}, headers={"X-Session-ID": "sess_Alpha"})
    assert rep_res_a.status_code == 200, f"Owner report preview failed: {rep_res_a.text}"
    assert "executive_summary" in rep_res_a.json()

    # 2. Session A (Owner) exports Excel
    excel_res_a = client.post(f"/api/v1/datasets/{id_a}/reports/export/excel", json={}, headers={"X-Session-ID": "sess_Alpha"})
    assert excel_res_a.status_code == 200
    assert len(excel_res_a.content) > 100

    # 3. Session B (Unauthorized) attempts report preview -> 404
    rep_res_b = client.post(f"/api/v1/datasets/{id_a}/reports/generate", json={}, headers={"X-Session-ID": "sess_Beta"})
    assert rep_res_b.status_code == 404

    # 4. Session B (Unauthorized) attempts Excel export -> 404
    excel_res_b = client.post(f"/api/v1/datasets/{id_a}/reports/export/excel", json={}, headers={"X-Session-ID": "sess_Beta"})
    assert excel_res_b.status_code == 404

    # 5. Session B (Unauthorized) attempts PDF export -> 404
    pdf_res_b = client.post(f"/api/v1/datasets/{id_a}/reports/export/pdf", json={}, headers={"X-Session-ID": "sess_Beta"})
    assert pdf_res_b.status_code == 404

    # 6. Anonymous (Missing Header) attempts report preview -> 404
    rep_res_anon = client.post(f"/api/v1/datasets/{id_a}/reports/generate", json={})
    assert rep_res_anon.status_code == 404

    # 7. Anonymous (Missing Header) attempts Excel export -> 404
    excel_res_anon = client.post(f"/api/v1/datasets/{id_a}/reports/export/excel", json={})
    assert excel_res_anon.status_code == 404


def test_backward_compatibility_unowned_datasets(client, test_storage):
    """Unowned datasets (session_id=None, e.g. from existing test suites) remain accessible."""
    id_legacy = _upload_csv(client, session_id=None, filename="legacy_test.csv")

    # Can be fetched without session header
    resp_no_sess = client.get(f"/api/v1/datasets/{id_legacy}")
    assert resp_no_sess.status_code == 200

    # Can be fetched with session header
    resp_with_sess = client.get(f"/api/v1/datasets/{id_legacy}", headers={"X-Session-ID": "sess_Gamma"})
    assert resp_with_sess.status_code == 200

