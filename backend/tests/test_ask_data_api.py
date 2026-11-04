import io
import json
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.ai.gemini_provider import GeminiProvider
from app.services.dataset_storage import dataset_storage


client = TestClient(app)


def upload_sample_dataset(csv_content: str, filename: str = "test_ask.csv") -> str:
    """Helper to upload a CSV dataset and return dataset_id."""
    file_bytes = csv_content.encode("utf-8")
    response = client.post(
        "/api/v1/datasets/upload",
        files={"file": (filename, io.BytesIO(file_bytes), "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()["overview"]["id"]


def test_basic_numeric_mean_and_fact_grounding():
    """Test arithmetic mean question and verify exact Pandas result."""
    csv_data = "item,price\nA,10.0\nB,20.0\nC,30.0\nD,40.0\n"
    ds_id = upload_sample_dataset(csv_data)

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "What is the average price?", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["primary_metric"] is not None
    # (10 + 20 + 30 + 40) / 4 = 25.0
    assert float(data["primary_metric"]["value"]) == 25.0
    assert "25.00" in data["primary_metric"]["formatted"]
    assert "price" in [c.lower() for c in data["columns_used"]]
    assert len(data["grounded_facts"]) >= 1
    assert any("price" in f["column_name"].lower() for f in data["grounded_facts"] if f["column_name"])


def test_group_by_comparison_operation():
    """Test group-by breakdown across categorical segments."""
    csv_data = "category,revenue\nElectronics,500\nElectronics,300\nApparel,200\nApparel,100\nBooks,50\n"
    ds_id = upload_sample_dataset(csv_data)

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "What is the total revenue by category?", "include_chart": True},
    )
    assert res.status_code == 200
    data = res.json()

    assert len(data["tabular_data"]) >= 3
    # Electronics sum should be 800
    electronics_row = next((r for r in data["tabular_data"] if r["category"] == "Electronics"), None)
    assert electronics_row is not None
    assert float(electronics_row["sum_revenue"]) == 800.0

    # Verify chart generation
    assert data["chart"] is not None
    assert data["chart"]["chart_type"] == "bar"


def test_value_counts_distribution_query():
    """Test frequency count on categorical column."""
    csv_data = "city,pop\nNew York,100\nLondon,200\nNew York,150\nParis,50\nNew York,300\n"
    ds_id = upload_sample_dataset(csv_data)

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Show distribution of city", "include_chart": True},
    )
    assert res.status_code == 200
    data = res.json()

    assert len(data["tabular_data"]) >= 1
    ny_row = next((r for r in data["tabular_data"] if r["city"] == "New York"), None)
    assert ny_row is not None
    assert ny_row["count"] == 3


def test_missing_values_inspection_query():
    """Test missing value inspection question."""
    csv_data = "id,age,score\n1,25,90\n2,,85\n3,, \n4,30,95\n"
    ds_id = upload_sample_dataset(csv_data)

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Which columns have missing values?", "include_chart": True},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["primary_metric"] is not None
    # age has missing values
    assert any("age" in r.get("column_name", "").lower() for r in data["tabular_data"])


def test_correlation_analysis_query():
    """Test correlation between two numeric columns."""
    csv_data = "hours,score\n1,50\n2,60\n3,70\n4,80\n5,90\n"
    ds_id = upload_sample_dataset(csv_data)

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "What is the correlation between hours and score?", "include_chart": True},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["primary_metric"] is not None
    # Perfect linear correlation r = 1.0
    assert float(data["primary_metric"]["value"]) == 1.0
    assert data["chart"] is not None
    assert data["chart"]["chart_type"] == "scatter"


def test_top_ranking_query():
    """Test top N ranking question."""
    csv_data = "product,sales\nA,100\nB,500\nC,300\nD,900\nE,200\n"
    ds_id = upload_sample_dataset(csv_data)

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Top 3 products by sales", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()

    assert len(data["tabular_data"]) <= 3
    first_row = data["tabular_data"][0]
    val = first_row.get("max_sales") or first_row.get("sales")
    assert float(val) == 900.0


def test_invalid_column_graceful_handling():
    """Test asking about non-existent column without 500 crashes."""
    csv_data = "colA,colB\n1,2\n3,4\n"
    ds_id = upload_sample_dataset(csv_data)

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "What is the average of non_existent_column_xyz?", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()
    # Should safely return clarification or direct explanation
    assert data["direct_answer"] is not None
    assert "non_existent_column_xyz" in data["direct_answer"] or data["is_ambiguous"] is True


def test_ambiguous_question_returns_clarification():
    """Test vague query returns clarification and suggestions."""
    csv_data = "col1,col2\n10,20\n30,40\n"
    ds_id = upload_sample_dataset(csv_data)

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "tell me something interesting", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_ambiguous"] is True
    assert len(data["suggested_follow_ups"]) >= 1


def test_arbitrary_code_injection_prevention():
    """Test that input containing Python or SQL code is never executed."""
    csv_data = "secret,val\n1,10\n2,20\n"
    ds_id = upload_sample_dataset(csv_data)

    malicious_inputs = [
        "__import__('os').system('echo hacked')",
        "eval('1 + 1')",
        "DROP TABLE users; SELECT * FROM secret;",
        "exec('import shutil; shutil.rmtree(\".\")')",
    ]

    for attack in malicious_inputs:
        res = client.post(
            f"/api/v1/datasets/{ds_id}/ask",
            json={"question": attack, "include_chart": False},
        )
        assert res.status_code == 200
        # No system error, handled safely as plain text
        data = res.json()
        assert data["direct_answer"] is not None


def test_conversation_persistence_and_clearing():
    """Test chat history retrieval and clearing."""
    csv_data = "a,b\n1,10\n2,20\n"
    ds_id = upload_sample_dataset(csv_data)

    # Ask first question
    client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "What is the sum of b?", "include_chart": False},
    )

    # Retrieve history
    hist_res = client.get(f"/api/v1/datasets/{ds_id}/conversation")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["total_messages"] >= 2  # user + assistant

    # Clear conversation
    del_res = client.delete(f"/api/v1/datasets/{ds_id}/conversation")
    assert del_res.status_code == 200

    # Verify empty history
    cleared_res = client.get(f"/api/v1/datasets/{ds_id}/conversation")
    assert cleared_res.json()["total_messages"] == 0


def test_dataset_isolation():
    """Test conversations on dataset A and dataset B remain strictly separated."""
    dsA = upload_sample_dataset("colA\n100\n", "dsA.csv")
    dsB = upload_sample_dataset("colB\n999\n", "dsB.csv")

    client.post(f"/api/v1/datasets/{dsA}/ask", json={"question": "What is colA?"})
    client.post(f"/api/v1/datasets/{dsB}/ask", json={"question": "What is colB?"})

    histA = client.get(f"/api/v1/datasets/{dsA}/conversation").json()
    histB = client.get(f"/api/v1/datasets/{dsB}/conversation").json()

    assert all("colB" not in m["content"] for m in histA["messages"])
    assert all("colA" not in m["content"] for m in histB["messages"])


def test_cleaned_dataset_calculates_against_clean_version():
    """Test asking questions on a cleaned dataset uses the cleaned rows."""
    csv_data = "col,val\nA,10\nB,\nC,30\n"
    parent_id = upload_sample_dataset(csv_data, "raw_data.csv")

    # Apply mean imputation on val
    apply_res = client.post(
        f"/api/v1/datasets/{parent_id}/cleaning/apply",
        json={
            "operation_type": "missing_values",
            "column_name": "val",
            "strategy": "mean_replacement",
        },
    )
    assert apply_res.status_code == 200
    clean_id = apply_res.json()["cleaned_dataset_id"]

    # Ask question on cleaned dataset
    res = client.post(
        f"/api/v1/datasets/{clean_id}/ask",
        json={"question": "Which columns have missing values?", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()
    # Missing values should be 0 on cleaned dataset
    assert data["primary_metric"]["value"] == 0


def test_suggested_questions_endpoint():
    """Test suggested questions endpoint returns schema-informed prompts."""
    csv_data = "category,price,created_at\nTech,100,2024-01-01\nFood,20,2024-01-02\n"
    ds_id = upload_sample_dataset(csv_data)

    res = client.get(f"/api/v1/datasets/{ds_id}/suggested-questions")
    assert res.status_code == 200
    prompts = res.json()["prompts"]
    assert len(prompts) >= 3
    assert any("price" in p.lower() for p in prompts)


def test_company_names_starting_with_letter():
    """Test Question 1: 'Which company's name starts with I?' on company dataset."""
    csv_data = "Company Logo (URL),Company Name,Company Website\nhttps://logo.com/inf.png,Infosys,https://infosys.com\nhttps://logo.com/ibm.png,IBM,https://ibm.com\nhttps://logo.com/ms.png,Microsoft,https://microsoft.com\nhttps://logo.com/int.png,Intel,https://intel.com\n"
    ds_id = upload_sample_dataset(csv_data, "companies.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Which company's name starts with I?", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["primary_metric"] is not None
    # Infosys, IBM, Intel -> 3 matches
    assert data["primary_metric"]["value"] == 3
    assert "Company Name" in data["columns_used"]
    assert "Company Logo (URL)" not in data["columns_used"]
    names = [r.get("Company Name") for r in data["tabular_data"]]
    assert "Infosys" in names
    assert "IBM" in names
    assert "Intel" in names
    assert "Microsoft" not in names


def test_company_names_containing_keyword():
    """Test Question 2: 'Show companies containing Tech'."""
    csv_data = "Company Logo (URL),Company Name,Company Website\nhttp://l1.png,BioTech Corp,http://biotech.com\nhttp://l2.png,FinTech Solutions,http://fintech.com\nhttp://l3.png,Apex Logistics,http://apex.com\n"
    ds_id = upload_sample_dataset(csv_data, "tech_companies.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Show companies containing Tech", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["primary_metric"] is not None
    assert data["primary_metric"]["value"] == 2
    names = [r.get("Company Name") for r in data["tabular_data"]]
    assert "BioTech Corp" in names
    assert "FinTech Solutions" in names
    assert "Apex Logistics" not in names


def test_unique_categorical_values_query():
    """Test Question 3: 'List all unique company names'."""
    csv_data = "Company Name,Department\nGoogle,Cloud\nGoogle,Search\nApple,Hardware\nAmazon,Retail\nApple,Services\n"
    ds_id = upload_sample_dataset(csv_data, "unique_companies.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "List all unique company names", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["primary_metric"] is not None
    assert data["primary_metric"]["value"] == 3
    assert len(data["tabular_data"]) == 3


def test_most_frequently_appearing_category():
    """Test Question 4: 'Which company appears most frequently?'."""
    csv_data = "Company Name,Revenue\nMeta,100\nMeta,200\nMeta,300\nNetflix,150\nNetflix,120\nUber,80\n"
    ds_id = upload_sample_dataset(csv_data, "frequency.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Which company appears most frequently?", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["primary_metric"] is not None
    assert "Meta" in data["primary_metric"]["formatted"]
    assert "Meta" in data["direct_answer"]


def test_general_dataset_overview_query():
    """Test Question 5: 'Which data contains this uploaded file?' / 'Explain this uploaded dataset'."""
    csv_data = "Company Name,Employees,Country\nTCS,500000,India\nInfosys,300000,India\nWipro,250000,India\n"
    ds_id = upload_sample_dataset(csv_data, "overview_test.csv")

    for q in ["Which data contains this uploaded file?", "Explain this uploaded dataset", "What information is available in this file?"]:
        res = client.post(
            f"/api/v1/datasets/{ds_id}/ask",
            json={"question": q, "include_chart": False},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_ambiguous"] is False
        assert data["primary_metric"] is not None
        assert "3 rows" in data["primary_metric"]["formatted"]
        assert len(data["tabular_data"]) == 3
        assert "Company Name" in data["direct_answer"] or "Employees" in data["direct_answer"]


def test_column_disambiguation_avoids_logo_url():
    """Test Question 6: Asking about company entity never selects Logo URL."""
    csv_data = "Company Logo (URL),Company Name,Company Website\nhttp://a.png,Alpha,http://a.com\nhttp://b.png,Beta,http://b.com\n"
    ds_id = upload_sample_dataset(csv_data, "disambig.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Which company starts with A?", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert "Company Name" in data["columns_used"]
    assert "Company Logo (URL)" not in data["columns_used"]

    logo_res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "What is the distribution of Company Logo (URL)?", "include_chart": False},
    )
    assert logo_res.status_code == 200
    logo_data = logo_res.json()
    assert "Company Logo (URL)" in logo_data["columns_used"]


def test_no_matching_records_returns_clean_zero_matches():
    """Test Question 7: Filter resulting in 0 matches returns graceful explanation."""
    csv_data = "Company Name,Sector\nAcme Corp,Retail\nGlobex,Industrial\n"
    ds_id = upload_sample_dataset(csv_data, "no_matches.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Which company starts with Z?", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["primary_metric"]["value"] == 0
    assert "No records found" in data["direct_answer"]
    assert len(data["tabular_data"]) == 0


def test_text_filtering_on_generic_dataset():
    """Test Question 8: Generic text filtering on non-company dataset (e.g. destination)."""
    csv_data = "destination,passengers\nTokyo,500\nToronto,300\nParis,200\nTaipei,150\n"
    ds_id = upload_sample_dataset(csv_data, "flights.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Which destination starts with T?", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["primary_metric"]["value"] == 3
    destinations = [r.get("destination") for r in data["tabular_data"]]
    assert "Tokyo" in destinations
    assert "Toronto" in destinations
    assert "Taipei" in destinations
    assert "Paris" not in destinations


def test_offline_deterministic_fallback_text_query():
    """Test Question 10: Text queries work deterministically when unkeyed or offline."""
    csv_data = "Company Name,City\nInnoTech,Bangalore\nInfosys,Bangalore\nGoogle,Mountain View\n"
    ds_id = upload_sample_dataset(csv_data, "offline_test.csv")

    res = client.post(
        f"/api/v1/datasets/{ds_id}/ask",
        json={"question": "Which company starts with I?", "include_chart": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "statistical_fallback"
    assert data["primary_metric"]["value"] == 2

