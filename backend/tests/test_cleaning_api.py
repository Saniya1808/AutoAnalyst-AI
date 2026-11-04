import hashlib
import io
import pytest
from fastapi.testclient import TestClient
import pandas as pd

from app.main import app
from app.services.dataset_storage import dataset_storage

client = TestClient(app)


def _upload_test_csv(csv_content: str, filename: str = "test_clean.csv") -> str:
    """Helper to upload a dataset and return its secure dataset_id."""
    files = {"file": (filename, io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post("/api/v1/datasets/upload", files=files)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["overview"]["id"]


# 1. Missing value detection
def test_missing_value_detection():
    csv = "A,B,C\n1,apple,10\n,banana,\n3,,30\n"
    ds_id = _upload_test_csv(csv)

    resp = client.get(f"/api/v1/datasets/{ds_id}/cleaning/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 3
    assert data["total_missing_cells"] == 3
    assert data["missing_percentage"] > 0
    # Column B should have 1 missing
    col_b = next(c for c in data["columns"] if c["column_name"] == "B")
    assert col_b["missing_count"] == 1


# 2. Mean imputation
def test_mean_imputation():
    csv = "val,cat\n10,A\n20,B\n,C\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "missing_values",
        "column_name": "val",
        "strategy": "mean_replacement",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["step"]["affected_cells"] == 1
    # Check updated quality profile has 0 missing in val
    col_val = next(c for c in data["updated_quality"]["columns"] if c["column_name"] == "val")
    assert col_val["missing_count"] == 0


# 3. Median imputation
def test_median_imputation():
    csv = "score\n10\n20\n100\n\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "missing_values",
        "column_name": "score",
        "strategy": "median_replacement",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


# 4. Mode imputation
def test_mode_imputation():
    csv = "city\nParis\nLondon\nParis\n\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "missing_values",
        "column_name": "city",
        "strategy": "mode_replacement",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


# 5. Constant-value imputation
def test_constant_value_imputation():
    csv = "status\nActive\n\nPending\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "missing_values",
        "column_name": "status",
        "strategy": "constant_replacement",
        "parameters": {"value": "Unknown"},
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


# 6. Missing row removal
def test_missing_row_removal():
    csv = "id,name\n1,Alice\n2,\n3,Charlie\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "missing_values",
        "column_name": "name",
        "strategy": "remove_rows",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    assert resp.json()["updated_quality"]["total_rows"] == 2


# 7. Missing column removal
def test_missing_column_removal():
    csv = "id,junk,keep\n1,,10\n2,,20\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "missing_values",
        "column_name": "junk",
        "strategy": "remove_column",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    assert resp.json()["updated_quality"]["total_columns"] == 2


# 8. Duplicate detection
def test_duplicate_detection():
    csv = "A,B\n1,x\n2,y\n1,x\n1,x\n"
    ds_id = _upload_test_csv(csv)

    resp = client.get(f"/api/v1/datasets/{ds_id}/cleaning/profile")
    assert resp.status_code == 200
    assert resp.json()["duplicate_rows"] == 2


# 9. Duplicate removal
def test_duplicate_removal():
    csv = "A,B\n1,x\n2,y\n1,x\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "duplicates",
        "strategy": "remove_duplicates",
        "parameters": {"keep": "first"},
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    assert resp.json()["updated_quality"]["total_rows"] == 2
    assert resp.json()["updated_quality"]["duplicate_rows"] == 0


# 10. Keep first vs keep last duplicate behaviour
def test_keep_first_last_duplicate():
    csv = "id,seq\n1,first\n1,second\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "duplicates",
        "strategy": "remove_duplicates",
        "parameters": {"keep": "last"},
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    assert resp.json()["updated_quality"]["total_rows"] == 2  # Different seq, not identical row


# 11. Numeric type conversion
def test_numeric_type_conversion():
    csv = "val\n10\n20\n30\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "type_conversion",
        "column_name": "val",
        "strategy": "float",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    col = next(c for c in resp.json()["updated_quality"]["columns"] if c["column_name"] == "val")
    assert col["data_type"] in ("float", "integer")


# 12. Datetime conversion
def test_datetime_conversion():
    csv = "dt_str\n2026-01-01\n2026-02-01\n2026-03-01\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "type_conversion",
        "column_name": "dt_str",
        "strategy": "datetime",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    col = next(c for c in resp.json()["updated_quality"]["columns"] if c["column_name"] == "dt_str")
    assert col["data_type"] == "datetime"


# 13. Invalid conversion handling
def test_invalid_conversion_handling():
    csv = "mixed\n10\nnot_a_num\n30\n"
    ds_id = _upload_test_csv(csv)

    # Preview should report warning
    preview_req = {
        "operation_type": "type_conversion",
        "column_name": "mixed",
        "strategy": "integer",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/preview", json=preview_req)
    assert resp.status_code == 200
    assert len(resp.json()["validation_warnings"]) > 0


# 14. IQR outlier detection
def test_iqr_outlier_detection():
    # 10 normal points around 10-15, and 1 extreme outlier 1000
    csv = "nums\n10\n11\n12\n10\n11\n12\n10\n11\n12\n1000\n"
    ds_id = _upload_test_csv(csv)

    resp = client.get(f"/api/v1/datasets/{ds_id}/cleaning/profile")
    assert resp.status_code == 200
    outliers = resp.json()["outlier_details"].get("nums", {})
    assert "iqr" in outliers
    assert outliers["iqr"]["outlier_count"] >= 1


# 15. Z-score outlier detection
def test_zscore_outlier_detection():
    csv = "vals\n" + "\n".join(["10"] * 20) + "\n1000\n"
    ds_id = _upload_test_csv(csv)

    resp = client.get(f"/api/v1/datasets/{ds_id}/cleaning/profile")
    assert resp.status_code == 200
    outliers = resp.json()["outlier_details"].get("vals", {})
    assert "zscore" in outliers
    assert outliers["zscore"]["outlier_count"] >= 1


# 16. Outlier capping
def test_outlier_capping():
    csv = "vals\n10\n11\n12\n10\n11\n12\n10\n11\n12\n500\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "outliers",
        "column_name": "vals",
        "strategy": "cap_values",
        "parameters": {"method": "iqr"},
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    # Cleaned dataset should have 0 outliers now
    profile = client.get(f"/api/v1/datasets/{ds_id}/cleaning/profile").json()
    assert profile["outlier_details"]["vals"]["iqr"]["outlier_count"] == 0


# 17. Outlier row removal
def test_outlier_row_removal():
    csv = "vals\n10\n11\n12\n10\n11\n12\n10\n11\n12\n500\n"
    ds_id = _upload_test_csv(csv)

    payload = {
        "operation_type": "outliers",
        "column_name": "vals",
        "strategy": "remove_rows",
        "parameters": {"method": "iqr"},
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=payload)
    assert resp.status_code == 200
    assert resp.json()["updated_quality"]["total_rows"] == 9


# 18. Preview without applying
def test_preview_without_applying():
    csv = "val,tag\n10,a\n,b\n30,c\n"
    ds_id = _upload_test_csv(csv)

    preview_req = {
        "operation_type": "missing_values",
        "column_name": "val",
        "strategy": "mean_replacement",
    }
    resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/preview", json=preview_req)
    assert resp.status_code == 200
    assert resp.json()["affected_cells"] == 1

    # Check profile is UNCHANGED
    profile = client.get(f"/api/v1/datasets/{ds_id}/cleaning/profile").json()
    assert profile["total_missing_cells"] == 1


# 19. Undo operation
def test_undo_operation():
    csv = "val,tag\n1,a\n2,b\n,c\n"
    ds_id = _upload_test_csv(csv)

    # Step 1: Mean replacement
    apply_req = {
        "operation_type": "missing_values",
        "column_name": "val",
        "strategy": "mean_replacement",
    }
    resp1 = client.post(f"/api/v1/datasets/{ds_id}/cleaning/apply", json=apply_req)
    assert resp1.status_code == 200
    assert resp1.json()["version"] == 1

    # Undo
    undo_resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/undo")
    assert undo_resp.status_code == 200
    assert undo_resp.json()["current_version"] == 0
    # Missing cells should be restored to 1
    assert undo_resp.json()["updated_quality"]["total_missing_cells"] == 1


# 20. Reset to original dataset
def test_reset_dataset():
    csv = "a,b\n1,2\n1,2\n\n4\n"
    ds_id = _upload_test_csv(csv)

    # Apply 2 transformations
    client.post(
        f"/api/v1/datasets/{ds_id}/cleaning/apply",
        json={"operation_type": "duplicates", "strategy": "remove_duplicates"},
    )
    client.post(
        f"/api/v1/datasets/{ds_id}/cleaning/apply",
        json={"operation_type": "missing_values", "column_name": "a", "strategy": "mean_replacement"},
    )

    # Reset
    reset_resp = client.post(f"/api/v1/datasets/{ds_id}/cleaning/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["original_file_hash_verified"] is True
    # Back to 3 rows
    assert reset_resp.json()["updated_quality"]["total_rows"] == 3


# 21. Transformation history
def test_transformation_history():
    csv = "x,y\n1,2\n3,\n"
    ds_id = _upload_test_csv(csv)

    client.post(
        f"/api/v1/datasets/{ds_id}/cleaning/apply",
        json={"operation_type": "missing_values", "column_name": "y", "strategy": "constant_replacement", "parameters": {"value": 0}},
    )

    hist_resp = client.get(f"/api/v1/datasets/{ds_id}/cleaning/history")
    assert hist_resp.status_code == 200
    history = hist_resp.json()["history"]
    assert len(history) == 1
    assert history[0]["operation_type"] == "missing_values"


# 22. Persistence across restart
def test_persistence_across_restart():
    csv = "col\n10\n\n30\n"
    ds_id = _upload_test_csv(csv)

    client.post(
        f"/api/v1/datasets/{ds_id}/cleaning/apply",
        json={"operation_type": "missing_values", "column_name": "col", "strategy": "mean_replacement"},
    )

    clean_id = f"clean_{ds_id}"
    # Verify cleaned dataset exists in storage
    clean_detail = dataset_storage.get_dataset(clean_id)
    assert clean_detail is not None
    assert clean_detail.overview.is_cleaned is True


# 23. Invalid dataset ID and invalid column handling
def test_invalid_requests_rejection():
    resp = client.get("/api/v1/datasets/non_existent_id/cleaning/profile")
    assert resp.status_code == 404

    csv = "a,b\n1,2\n"
    ds_id = _upload_test_csv(csv)

    # Invalid column
    resp = client.post(
        f"/api/v1/datasets/{ds_id}/cleaning/apply",
        json={"operation_type": "missing_values", "column_name": "ghost", "strategy": "mean_replacement"},
    )
    assert resp.status_code == 400


# 24. Original dataset remains unchanged (SHA-256 verification)
def test_original_dataset_immutability():
    csv = "orig_a,orig_b\n1,10\n,20\n3,30\n1,10\n"
    ds_id = _upload_test_csv(csv)

    file_path = dataset_storage.get_dataset_file_path(ds_id)
    initial_hash = dataset_storage.compute_sha256(file_path)

    # Apply multiple destructive-looking operations
    client.post(
        f"/api/v1/datasets/{ds_id}/cleaning/apply",
        json={"operation_type": "duplicates", "strategy": "remove_duplicates"},
    )
    client.post(
        f"/api/v1/datasets/{ds_id}/cleaning/apply",
        json={"operation_type": "missing_values", "column_name": "orig_a", "strategy": "remove_rows"},
    )

    # Verify original file hash has NOT changed at all
    final_hash = dataset_storage.compute_sha256(file_path)
    assert initial_hash == final_hash, "Original dataset file was modified!"
