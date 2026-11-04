import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from app.core.json_encoder import sanitize_for_json
from app.models.dataset import ColumnProfile, DatasetOverview, DatasetPreview


def format_bytes(size_bytes: int) -> str:
    """Format bytes into human-readable string (e.g. 1.2 MB)."""
    if size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    return f"{size:.1f} {units[unit_index]}"


def infer_column_type(series: pd.Series) -> str:
    """Infer high-level semantic data type for a Pandas Series."""
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_numeric_dtype(series):
        return "float"
    return "string"


def profile_column(series: pd.Series, position: int) -> ColumnProfile:
    """Compute comprehensive statistics for a single dataset column."""
    name = str(series.name)
    total_count = len(series)
    non_null_count = int(series.count())
    null_count = total_count - non_null_count
    null_percentage = round((null_count / total_count * 100.0) if total_count > 0 else 0.0, 2)
    
    raw_dtype = str(series.dtype)
    data_type = infer_column_type(series)

    # Distinct values
    try:
        unique_count = int(series.nunique(dropna=True))
    except Exception:
        unique_count = 0
    
    is_unique = (unique_count == non_null_count and non_null_count > 0)

    # Sample non-null values
    sample_values: List[Any] = []
    try:
        samples = series.dropna().unique()[:5]
        sample_values = [sanitize_for_json(val) for val in samples]
    except Exception:
        sample_values = []

    # Initialize stats
    stat_min: Optional[float] = None
    stat_max: Optional[float] = None
    stat_mean: Optional[float] = None
    stat_std: Optional[float] = None
    stat_median: Optional[float] = None
    stat_q25: Optional[float] = None
    stat_q75: Optional[float] = None
    zeros_count: Optional[int] = None
    negative_count: Optional[int] = None
    top_values: Optional[List[Dict[str, Any]]] = None
    min_date: Optional[str] = None
    max_date: Optional[str] = None

    if data_type in ("integer", "float"):
        clean_num = pd.to_numeric(series, errors="coerce").dropna()
        if len(clean_num) > 0:
            try:
                min_v = float(clean_num.min())
                if not (math.isnan(min_v) or math.isinf(min_v)):
                    stat_min = round(min_v, 4)
            except Exception:
                pass

            try:
                max_v = float(clean_num.max())
                if not (math.isnan(max_v) or math.isinf(max_v)):
                    stat_max = round(max_v, 4)
            except Exception:
                pass

            try:
                mean_v = float(clean_num.mean())
                if not (math.isnan(mean_v) or math.isinf(mean_v)):
                    stat_mean = round(mean_v, 4)
            except Exception:
                pass

            try:
                if len(clean_num) > 1:
                    std_v = float(clean_num.std(ddof=1))
                    if not (math.isnan(std_v) or math.isinf(std_v)):
                        stat_std = round(std_v, 4)
            except Exception:
                pass

            try:
                med_v = float(clean_num.median())
                if not (math.isnan(med_v) or math.isinf(med_v)):
                    stat_median = round(med_v, 4)
            except Exception:
                pass

            try:
                q25_v = float(clean_num.quantile(0.25))
                if not (math.isnan(q25_v) or math.isinf(q25_v)):
                    stat_q25 = round(q25_v, 4)
            except Exception:
                pass

            try:
                q75_v = float(clean_num.quantile(0.75))
                if not (math.isnan(q75_v) or math.isinf(q75_v)):
                    stat_q75 = round(q75_v, 4)
            except Exception:
                pass

            try:
                zeros_count = int((clean_num == 0).sum())
                negative_count = int((clean_num < 0).sum())
            except Exception:
                pass

    elif data_type == "datetime":
        try:
            valid_dates = pd.to_datetime(series, errors="coerce").dropna()
            if len(valid_dates) > 0:
                min_date = valid_dates.min().isoformat()
                max_date = valid_dates.max().isoformat()
        except Exception:
            pass

    # For categorical/string/boolean/integer with low cardinality, provide top values
    if data_type in ("string", "boolean") or (data_type == "integer" and unique_count <= 20):
        try:
            top_counts = series.dropna().astype(str).value_counts().head(5)
            top_values = [
                {"value": str(val), "count": int(count)}
                for val, count in top_counts.items()
            ]
        except Exception:
            top_values = []

    return ColumnProfile(
        name=name,
        position=position,
        data_type=data_type,
        raw_dtype=raw_dtype,
        non_null_count=non_null_count,
        null_count=null_count,
        null_percentage=null_percentage,
        unique_count=unique_count,
        is_unique=is_unique,
        sample_values=sample_values,
        min=stat_min,
        max=stat_max,
        mean=stat_mean,
        std=stat_std,
        median=stat_median,
        q25=stat_q25,
        q75=stat_q75,
        zeros_count=zeros_count,
        negative_count=negative_count,
        top_values=top_values,
        min_date=min_date,
        max_date=max_date,
    )


def compute_dataset_overview(
    df: pd.DataFrame,
    dataset_id: str,
    filename: str,
    file_size_bytes: int,
    file_type: str,
    uploaded_at: str,
) -> DatasetOverview:
    """Compute high-level summary metadata and quality metrics for a DataFrame."""
    row_count = int(len(df))
    column_count = int(len(df.columns))
    total_cells = row_count * column_count
    
    missing_cells = int(df.isna().sum().sum())
    missing_percentage = round((missing_cells / total_cells * 100.0) if total_cells > 0 else 0.0, 2)

    try:
        duplicate_rows = int(df.duplicated().sum())
    except Exception:
        duplicate_rows = 0
    duplicate_percentage = round((duplicate_rows / row_count * 100.0) if row_count > 0 else 0.0, 2)

    try:
        memory_usage_bytes = int(df.memory_usage(deep=True).sum())
    except Exception:
        memory_usage_bytes = 0
    memory_usage_human = format_bytes(memory_usage_bytes)

    return DatasetOverview(
        id=dataset_id,
        filename=filename,
        file_size_bytes=file_size_bytes,
        file_type=file_type,
        row_count=row_count,
        column_count=column_count,
        total_cells=total_cells,
        missing_cells=missing_cells,
        missing_percentage=missing_percentage,
        duplicate_rows=duplicate_rows,
        duplicate_percentage=duplicate_percentage,
        memory_usage_bytes=memory_usage_bytes,
        memory_usage_human=memory_usage_human,
        uploaded_at=uploaded_at,
    )


def generate_dataset_preview(
    df: pd.DataFrame,
    offset: int = 0,
    limit: int = 50,
) -> DatasetPreview:
    """Generate a clean, sanitized slice of dataset rows for frontend table rendering."""
    columns = [str(c) for c in df.columns]
    column_types = {str(c): infer_column_type(df[c]) for c in df.columns}
    
    total_rows = len(df)
    sliced = df.iloc[offset : offset + limit]
    
    # Convert dataframe to records safely
    # First convert timestamps and handles NaNs
    records: List[Dict[str, Any]] = []
    for _, row in sliced.iterrows():
        row_dict = {}
        for col_name in df.columns:
            val = row[col_name]
            # Check for NaN / null
            if pd.isna(val):
                row_dict[str(col_name)] = None
            else:
                row_dict[str(col_name)] = sanitize_for_json(val)
        records.append(row_dict)

    return DatasetPreview(
        columns=columns,
        column_types=column_types,
        rows=records,
        total_rows=total_rows,
        preview_rows_count=len(records),
        offset=offset,
        limit=limit,
    )
