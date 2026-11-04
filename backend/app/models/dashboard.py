from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DashboardKPI(BaseModel):
    total_rows: int = Field(..., description="Total rows in dataset or active filtered slice")
    total_columns: int = Field(..., description="Total columns in dataset")
    total_cells: int = Field(..., description="Total data cells (rows * cols)")
    missing_cells: int = Field(..., description="Count of empty or null cells")
    missing_percentage: float = Field(..., description="Percentage of missing cells")
    duplicate_rows: int = Field(..., description="Count of duplicate rows")
    duplicate_percentage: float = Field(..., description="Percentage of duplicate rows")
    data_completeness: float = Field(..., description="Overall completeness percentage (100 - missing_percentage)")
    selected_column: Optional[str] = None
    selected_column_stats: Optional[Dict[str, Any]] = None


class ChartConfig(BaseModel):
    chart_id: str = Field(..., description="Unique chart identifier")
    title: str = Field(..., description="Descriptive human-readable chart title")
    chart_type: str = Field(..., description="Type of chart: histogram, box, bar, pie, line, scatter")
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    group_column: Optional[str] = None
    aggregation: Optional[str] = None
    description: Optional[str] = None
    plotly_data: List[Dict[str, Any]] = Field(default_factory=list, description="Plotly trace objects")
    plotly_layout: Dict[str, Any] = Field(default_factory=dict, description="Plotly layout configuration")


class FilterRule(BaseModel):
    column: str = Field(..., description="Column name to filter")
    filter_type: str = Field(..., description="Filter type: categorical, numeric_range, datetime_range")
    selected_values: Optional[List[str]] = Field(default=None, description="For categorical filter")
    min_val: Optional[float] = Field(default=None, description="For numeric range filter minimum")
    max_val: Optional[float] = Field(default=None, description="For numeric range filter maximum")
    start_date: Optional[str] = Field(default=None, description="For datetime range start ISO")
    end_date: Optional[str] = Field(default=None, description="For datetime range end ISO")


class FilterOptions(BaseModel):
    categorical_filters: Dict[str, List[str]] = Field(default_factory=dict)
    numeric_filters: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    datetime_filters: Dict[str, Dict[str, str]] = Field(default_factory=dict)


class ColumnInfo(BaseModel):
    name: str
    data_type: str


class DashboardResponse(BaseModel):
    dataset_id: str
    filename: str
    kpis: DashboardKPI
    filter_options: FilterOptions
    active_filters: List[FilterRule] = Field(default_factory=list)
    recommended_charts: List[ChartConfig] = Field(default_factory=list)
    available_columns: List[ColumnInfo] = Field(default_factory=list)
    is_filtered: bool = False
    filtered_row_count: int
    total_row_count: int


class CustomChartRequest(BaseModel):
    chart_type: str = Field(..., description="histogram, box, bar, pie, line, scatter")
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    group_column: Optional[str] = None
    aggregation: Optional[str] = Field(default=None, description="sum, avg, count, min, max")
    filters: Optional[List[FilterRule]] = Field(default=None, description="Optional active filters to apply to chart")


class FilterDashboardRequest(BaseModel):
    filters: List[FilterRule] = Field(default_factory=list)
    selected_numeric_column: Optional[str] = None


class DrillDownRequest(BaseModel):
    category_column: str = Field(..., description="Column clicked for drilldown")
    category_value: str = Field(..., description="Value clicked for drilldown")
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    filters: Optional[List[FilterRule]] = Field(default=None)


class DrillDownResponse(BaseModel):
    category_column: str
    category_value: str
    total_matching_rows: int
    summary_stats: Dict[str, Any] = Field(default_factory=dict)
    sample_records: List[Dict[str, Any]] = Field(default_factory=list)

