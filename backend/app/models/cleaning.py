import hashlib
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DataQualityMetric(BaseModel):
    completeness_score: float = Field(..., description="Percentage of non-null cells across dataset")
    uniqueness_score: float = Field(..., description="Percentage of non-duplicate rows across dataset")
    validity_score: float = Field(..., description="Percentage of values adhering to expected semantic typing")
    overall_quality_score: float = Field(..., description="Weighted composite score: 0.50*Comp + 0.30*Valid + 0.20*Uniq")
    quality_grade: str = Field(..., description="Quality grade: Excellent, Good, Fair, Needs Attention")


class ColumnQualitySummary(BaseModel):
    column_name: str
    position: int
    data_type: str
    total_count: int
    missing_count: int
    missing_percentage: float
    unique_count: int
    is_numeric: bool
    outliers_iqr_count: Optional[int] = None
    outliers_zscore_count: Optional[int] = None


class IQRBoundaries(BaseModel):
    q1: float
    q3: float
    iqr: float
    lower_bound: float
    upper_bound: float
    outlier_count: int
    outlier_percentage: float


class ZScoreBoundaries(BaseModel):
    mean: float
    std: float
    threshold: float
    lower_bound: float
    upper_bound: float
    outlier_count: int
    outlier_percentage: float


class DataQualityProfile(BaseModel):
    dataset_id: str
    filename: str
    is_cleaned: bool = False
    parent_id: Optional[str] = None
    version: int = 0
    total_rows: int
    total_columns: int
    total_cells: int
    total_missing_cells: int
    missing_percentage: float
    duplicate_rows: int
    duplicate_percentage: float
    quality_metrics: DataQualityMetric
    columns: List[ColumnQualitySummary]
    outlier_details: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    original_file_hash: Optional[str] = None


class CleaningPreviewRequest(BaseModel):
    operation_type: str = Field(..., description="missing_values, duplicates, type_conversion, outliers")
    column_name: Optional[str] = None
    strategy: str = Field(..., description="Specific transformation strategy")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CleaningPreviewResponse(BaseModel):
    operation_type: str
    column_name: Optional[str] = None
    strategy: str
    affected_rows: int
    affected_cells: int
    is_valid: bool
    validation_warnings: List[str] = Field(default_factory=list)
    original_sample: List[Dict[str, Any]] = Field(default_factory=list)
    cleaned_sample: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str


class CleaningApplyRequest(BaseModel):
    operation_type: str = Field(..., description="missing_values, duplicates, type_conversion, outliers")
    column_name: Optional[str] = None
    strategy: str = Field(..., description="Specific transformation strategy")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TransformationStep(BaseModel):
    step_id: int
    version: int
    operation_type: str
    column_name: Optional[str] = None
    strategy: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    affected_rows: int
    affected_cells: int
    description: str
    timestamp: str


class CleaningApplyResponse(BaseModel):
    success: bool
    message: str
    cleaned_dataset_id: str
    version: int
    step: TransformationStep
    updated_quality: DataQualityProfile
    original_file_hash_verified: bool


class TransformationHistoryResponse(BaseModel):
    dataset_id: str
    cleaned_dataset_id: Optional[str] = None
    current_version: int = 0
    history: List[TransformationStep] = Field(default_factory=list)


class UndoResponse(BaseModel):
    success: bool
    message: str
    current_version: int
    remaining_steps: int
    cleaned_dataset_id: str
    updated_quality: DataQualityProfile


class ResetResponse(BaseModel):
    success: bool
    message: str
    original_dataset_id: str
    original_file_hash_verified: bool
    updated_quality: DataQualityProfile

