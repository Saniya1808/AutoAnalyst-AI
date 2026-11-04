import io
import json
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.ai.base_provider import BaseLLMProvider
from app.services.dataset_storage import dataset_storage

client = TestClient(app)


def _upload_test_csv(csv_content: str, filename: str = "test_ai.csv") -> str:
    """Helper to upload a test CSV and return its dataset ID."""
    files = {"file": (filename, io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post("/api/v1/datasets/upload", files=files)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["overview"]["id"]


# 1. Missing API Key: uses deterministic statistical fallback
def test_missing_api_key_activates_fallback():
    csv = "Survived,Age,Fare\n1,22,7.25\n0,38,71.28\n1,26,7.92\n0,35,53.1\n"
    ds_id = _upload_test_csv(csv, "titanic_mini.csv")

    with patch.object(settings, "GEMINI_API_KEY", None), patch.object(settings, "GOOGLE_API_KEY", None):
        resp = client.get(f"/api/v1/datasets/{ds_id}/understanding")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "statistical_fallback"
        assert data["provider"] in ("heuristic", "statistical_engine")
        assert "Maritime" in data["overview"]["domain"] or "Passenger" in data["overview"]["domain"] or "Titanic" in data["filename"]
        assert data["overview"]["detected_target_variable"]["column_name"] == "Survived"
        assert len(data["columns"]) == 3
        assert len(data["suggested_analysis"]["suggested_questions"]) >= 5


# 2. Valid AI Response with Mocked Gemini Provider
@pytest.mark.anyio
async def test_valid_ai_response_with_mocked_gemini():
    csv = "price,category,rating\n100,electronics,4.5\n200,books,4.8\n50,electronics,3.9\n"
    ds_id = _upload_test_csv(csv, "sales.csv")

    mock_gemini_output = {
        "overview": {
            "domain": "E-Commerce Product Sales",
            "likely_purpose": "Retail inventory pricing and rating performance analysis.",
            "executive_summary": "This catalog contains products with prices and customer review ratings.",
            "detected_target_variable": {
                "column_name": "price",
                "confidence": "high",
                "reasoning": "Product pricing is the primary commercial target.",
                "referenced_fact_ids": ["fact_1"]
            },
            "referenced_fact_ids": ["fact_1", "fact_2"]
        },
        "columns": [
            {
                "name": "price",
                "semantic_type": "integer",
                "business_meaning": "Retail price of the product item.",
                "is_key_feature": True,
                "is_identifier": False,
                "data_quality_note": None,
                "referenced_fact_ids": ["fact_1"]
            }
        ],
        "analytical_insights": {
            "key_observations": [
                {
                    "observation_type": "observed_fact",
                    "statement": "Electronics and books are the primary categories.",
                    "business_implication": "Focus marketing on high-rated book items.",
                    "referenced_fact_ids": ["fact_1"],
                    "is_verified_fact": True
                }
            ],
            "potential_relationships": [
                {
                    "primary_column": "price",
                    "secondary_column": "rating",
                    "relationship_description": "Price variation across ratings.",
                    "analytical_type": "correlation",
                    "referenced_fact_ids": ["fact_1"]
                }
            ],
            "business_relevance": "Drives product catalog assortment strategies."
        },
        "suggested_analysis": {
            "suggested_kpis": [
                {
                    "name": "Average Selling Price",
                    "calculation": "Mean(price)",
                    "purpose": "Track basket average",
                    "business_value": "Revenue optimization",
                    "target_column": "price"
                }
            ],
            "recommended_charts": [
                {
                    "chart_type": "bar",
                    "title": "Price by Category",
                    "x_column": "category",
                    "y_column": "price",
                    "aggregation": "avg",
                    "reason": "Identify highest value categories."
                }
            ],
            "suggested_questions": [
                "Does higher price correlate with lower review ratings?",
                "Which category generates the highest average margin?"
            ]
        }
    }

    with patch.object(settings, "GEMINI_API_KEY", "dummy_test_key"):
        with patch("app.services.ai.gemini_provider.GeminiProvider.generate_understanding", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_gemini_output

            resp = client.get(f"/api/v1/datasets/{ds_id}/understanding")
            assert resp.status_code == 200
            data = resp.json()
            assert data["mode"] == "ai_generated"
            assert data["provider"] == "gemini"
            assert data["overview"]["domain"] == "E-Commerce Product Sales"
            assert len(data["analytical_insights"]["key_observations"]) > 0


# 3. Provider failure / timeout gracefully falls back with retry flag
@pytest.mark.anyio
async def test_provider_timeout_graceful_fallback():
    csv = "A,B\n1,10\n2,20\n"
    ds_id = _upload_test_csv(csv)

    with patch.object(settings, "GEMINI_API_KEY", "dummy_test_key"):
        with patch("app.services.ai.gemini_provider.GeminiProvider.generate_understanding", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = TimeoutError("Gemini request timed out after 30 seconds.")

            resp = client.get(f"/api/v1/datasets/{ds_id}/understanding")
            assert resp.status_code == 200
            data = resp.json()
            # Must fall back gracefully rather than crash with 500
            assert data["mode"] == "statistical_fallback"
            assert data["can_retry"] is True
            assert "timed out" in (data["error_detail"] or "")


# 4. Dataset not found returns 404
def test_dataset_not_found():
    resp = client.get("/api/v1/datasets/ghost_dataset_id_123/understanding")
    assert resp.status_code == 404


# 5. Cache hit behavior
def test_cache_hit_returns_cached_data():
    csv = "x,y\n1,2\n3,4\n"
    ds_id = _upload_test_csv(csv)

    with patch.object(settings, "GEMINI_API_KEY", None):
        # First call: generates fresh
        resp1 = client.get(f"/api/v1/datasets/{ds_id}/understanding")
        assert resp1.status_code == 200
        assert resp1.json()["is_cached"] is False

        # Second call: returns cached
        resp2 = client.get(f"/api/v1/datasets/{ds_id}/understanding")
        assert resp2.status_code == 200
        assert resp2.json()["is_cached"] is True
        assert resp2.json()["snapshot_hash"] == resp1.json()["snapshot_hash"]


# 6. Force refresh bypasses cache
def test_force_refresh_bypasses_cache():
    csv = "a,b\n10,20\n30,40\n"
    ds_id = _upload_test_csv(csv)

    with patch.object(settings, "GEMINI_API_KEY", None):
        client.get(f"/api/v1/datasets/{ds_id}/understanding")

        # Refresh endpoint
        refresh_resp = client.post(f"/api/v1/datasets/{ds_id}/understanding/refresh")
        assert refresh_resp.status_code == 200
        assert refresh_resp.json()["is_cached"] is False


# 7. Original vs Cleaned dataset distinct understanding
def test_cleaned_dataset_distinct_understanding():
    csv = "score,tag\n10,A\n,B\n30,C\n"
    ds_id = _upload_test_csv(csv)

    # Impute missing in score
    apply_resp = client.post(
        f"/api/v1/datasets/{ds_id}/cleaning/apply",
        json={"operation_type": "missing_values", "column_name": "score", "strategy": "mean_replacement"}
    )
    assert apply_resp.status_code == 200
    clean_id = f"clean_{ds_id}"

    with patch.object(settings, "GEMINI_API_KEY", None):
        # Understanding for original
        orig_ai = client.get(f"/api/v1/datasets/{ds_id}/understanding").json()
        assert orig_ai["is_cleaned"] is False
        assert orig_ai["version"] == 0

        # Understanding for cleaned
        clean_ai = client.get(f"/api/v1/datasets/{clean_id}/understanding").json()
        assert clean_ai["is_cleaned"] is True
        assert clean_ai["version"] == 1
        assert clean_ai["snapshot_hash"] != orig_ai["snapshot_hash"]


# 8. Fact Grounding & Verification
def test_fact_grounding_and_downgrade():
    csv = "num_val\n10\n20\n30\n"
    ds_id = _upload_test_csv(csv)

    resp = client.get(f"/api/v1/datasets/{ds_id}/understanding")
    assert resp.status_code == 200
    data = resp.json()

    # Verify computed facts exist
    facts = data["computed_facts"]
    assert len(facts) > 0
    # Total rows fact must match actual length
    rows_fact = next(f for f in facts.values() if f["metric_name"] == "total_rows")
    assert rows_fact["value"] == 3


# 9. Wide dataset context extraction (safe handling of many columns)
def test_wide_dataset_handling():
    # 40 columns
    cols = [f"col_{i}" for i in range(40)]
    row1 = [str(i) for i in range(40)]
    csv = ",".join(cols) + "\n" + ",".join(row1) + "\n"
    ds_id = _upload_test_csv(csv, "wide_data.csv")

    resp = client.get(f"/api/v1/datasets/{ds_id}/understanding")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["columns"]) == 40

