import numpy as np
import pandas as pd
from app.services.profiler import (
    compute_dataset_overview,
    generate_dataset_preview,
    infer_column_type,
    profile_column,
)


def test_infer_column_type():
    assert infer_column_type(pd.Series([1, 2, 3])) == "integer"
    assert infer_column_type(pd.Series([1.5, 2.5, 3.5])) == "float"
    assert infer_column_type(pd.Series(["a", "b", "c"])) == "string"
    assert infer_column_type(pd.Series([True, False, True])) == "boolean"
    assert infer_column_type(pd.to_datetime(pd.Series(["2025-01-01", "2025-01-02"]))) == "datetime"


def test_profile_numeric_column_with_missing_and_zeros():
    data = pd.Series([10.0, 20.0, 0.0, -5.0, np.nan, 30.0], name="metric")
    profile = profile_column(data, 0)

    assert profile.name == "metric"
    assert profile.position == 0
    assert profile.data_type == "float"
    assert profile.non_null_count == 5
    assert profile.null_count == 1
    assert profile.null_percentage == round(1 / 6 * 100, 2)
    assert profile.min == -5.0
    assert profile.max == 30.0
    assert profile.mean == 11.0  # (10 + 20 + 0 - 5 + 30) / 5 = 55 / 5 = 11.0
    assert profile.median == 10.0
    assert profile.zeros_count == 1
    assert profile.negative_count == 1


def test_profile_categorical_column():
    data = pd.Series(["Sales", "Marketing", "Sales", "Engineering", "Sales", None], name="dept")
    profile = profile_column(data, 1)

    assert profile.name == "dept"
    assert profile.position == 1
    assert profile.data_type == "string"
    assert profile.non_null_count == 5
    assert profile.null_count == 1
    assert profile.unique_count == 3
    assert profile.is_unique is False
    assert profile.top_values is not None
    assert profile.top_values[0]["value"] == "Sales"
    assert profile.top_values[0]["count"] == 3


def test_compute_dataset_overview_duplicates():
    df = pd.DataFrame({
        "id": [1, 2, 2, 3],
        "name": ["A", "B", "B", "C"],
        "score": [10, 20, 20, np.nan],
    })
    overview = compute_dataset_overview(
        df=df,
        dataset_id="test_id_123",
        filename="test.csv",
        file_size_bytes=1024,
        file_type=".csv",
        uploaded_at="2026-11-01T00:00:00Z",
    )

    assert overview.row_count == 4
    assert overview.column_count == 3
    assert overview.total_cells == 12
    assert overview.missing_cells == 1
    assert overview.missing_percentage == round(1 / 12 * 100, 2)
    assert overview.duplicate_rows == 1
    assert overview.duplicate_percentage == 25.0
    assert overview.file_size_bytes == 1024


def test_generate_dataset_preview():
    df = pd.DataFrame({
        "col_a": [1, 2, 3],
        "col_b": ["x", None, "z"],
    })
    preview = generate_dataset_preview(df, offset=0, limit=2)
    assert preview.total_rows == 3
    assert preview.preview_rows_count == 2
    assert len(preview.rows) == 2
    assert preview.rows[1]["col_b"] is None
    assert preview.columns == ["col_a", "col_b"]

