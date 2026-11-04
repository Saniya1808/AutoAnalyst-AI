from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatasetOverview(BaseModel):
    id: str = Field(..., description="Secure unpredictable dataset identifier")
    filename: str = Field(..., description="Original filename")
    file_size_bytes: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File extension / format (.csv, .xlsx, .xls)")
    row_count: int = Field(..., description="Total rows in dataset")
    column_count: int = Field(..., description="Total columns in dataset")
    total_cells: int = Field(..., description="Total cell count (rows * columns)")
    missing_cells: int = Field(..., description="Total null or missing cells")
    missing_percentage: float = Field(..., description="Percentage of missing cells")
    duplicate_rows: int = Field(..., description="Count of duplicate rows")
    duplicate_percentage: float = Field(..., description="Percentage of duplicate rows")
    memory_usage_bytes: int = Field(..., description="Memory footprint in bytes")
    memory_usage_human: str = Field(..., description="Human-readable memory footprint")
    uploaded_at: str = Field(..., description="ISO 8601 upload timestamp")
    is_cleaned: bool = Field(default=False, description="Whether this is a cleaned dataset version")
    parent_id: Optional[str] = Field(default=None, description="Original dataset ID if this is a cleaned version")
    version: int = Field(default=0, description="Cleaned transformation version number")
    session_id: Optional[str] = Field(default=None, description="Anonymous session token isolating user datasets")
    is_sample: bool = Field(default=False, description="Whether this is a public sample dataset")


class ColumnProfile(BaseModel):
    name: str = Field(..., description="Column name")
    position: int = Field(..., description="0-indexed column position")
    data_type: str = Field(..., description="Simplified semantic type: integer, float, string, boolean, datetime")
    raw_dtype: str = Field(..., description="Pandas raw dtype string")
    non_null_count: int = Field(..., description="Number of non-null values")
    null_count: int = Field(..., description="Number of null values")
    null_percentage: float = Field(..., description="Null percentage (0-100)")
    unique_count: int = Field(..., description="Distinct non-null values count")
    is_unique: bool = Field(..., description="Whether column has 100% unique values")
    sample_values: List[Any] = Field(default_factory=list, description="Sample of distinct values")

    # Numeric statistics
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    median: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None
    zeros_count: Optional[int] = None
    negative_count: Optional[int] = None

    # Categorical statistics
    top_values: Optional[List[Dict[str, Any]]] = None

    # Datetime statistics
    min_date: Optional[str] = None
    max_date: Optional[str] = None


class DatasetPreview(BaseModel):
    columns: List[str]
    column_types: Dict[str, str]
    rows: List[Dict[str, Any]]
    total_rows: int
    preview_rows_count: int
    offset: int = 0
    limit: int = 50


class DatasetDetail(BaseModel):
    overview: DatasetOverview
    columns: List[ColumnProfile]
    preview: DatasetPreview


class DatasetListResponse(BaseModel):
    datasets: List[DatasetOverview]
    total_datasets: int
    total_rows_all: int
    total_columns_all: int


class DatasetDeleteResponse(BaseModel):
    message: str
    id: str
    success: bool = True

