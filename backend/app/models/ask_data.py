from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from app.models.dashboard import ChartConfig


# Strict allowed analytical operations
AnalyticalIntent = Literal[
    "aggregate_metric",
    "group_by_comparison",
    "correlation_analysis",
    "distribution_analysis",
    "trend_analysis",
    "period_benchmark",
    "temporal_anomaly",
    "seasonality_analysis",
    "ranking_top_bottom",
    "filter_inspection",
    "text_search",
    "distinct_values",
    "missing_value_inspection",
    "dataset_summary",
    "automated_insights",
    "best_worst_performers",
    "anomaly_detection",
    "business_recommendations",
    "data_quality_insights",
    "ambiguous_clarification",
    "unsupported_query",
]

AnalyticalOperation = Literal[
    "count",
    "sum",
    "mean",
    "median",
    "min",
    "max",
    "std",
    "percentage",
    "value_counts",
    "correlation",
    "distribution",
    "missing_summary",
    "filter_records",
    "unique_values",
    "overview",
    "discover_insights",
    "benchmark_performers",
    "detect_anomalies",
    "recommend_actions",
    "data_quality_audit",
    "analyze_trend",
    "benchmark_periods",
    "detect_temporal_anomalies",
    "detect_seasonality",
    "none",
]

FilterOperator = Literal[
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "not_in",
    "contains",
    "not_contains",
    "starts_with",
    "ends_with",
    "exact",
    "between",
]

SortDirection = Literal["ascending", "descending"]

ChartRecommendationType = Literal[
    "none",
    "bar",
    "line",
    "pie",
    "histogram",
    "scatter",
    "box",
]


class QueryFilterCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column: str = Field(..., description="Target dataset column name")
    operator: FilterOperator = Field(..., description="Safe comparison operator")
    value: Any = Field(..., description="Literal comparison value")


class QuerySortRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column: str = Field(..., description="Column to sort by")
    direction: SortDirection = Field(default="descending")


class QueryChartRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chart_type: ChartRecommendationType = Field(default="none")
    title: str = Field(default="")
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    group_column: Optional[str] = None
    aggregation: Optional[str] = None


class QueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str = Field(..., description="Unique ID for this analytical plan")
    intent: AnalyticalIntent = Field(..., description="High-level analytical objective")
    operation: AnalyticalOperation = Field(..., description="Strict Pandas aggregation operation")
    primary_column: Optional[str] = None
    secondary_column: Optional[str] = None
    group_by_columns: List[str] = Field(default_factory=list)
    filters: List[QueryFilterCondition] = Field(default_factory=list)
    sort: Optional[QuerySortRule] = None
    limit: Optional[int] = Field(default=10, ge=1, le=50)
    date_granularity: Optional[Literal["year", "quarter", "month", "week", "day", "day_of_week"]] = None
    period_mode: Optional[Literal["chronological", "cyclical"]] = None
    chart: Optional[QueryChartRecommendation] = None
    is_ambiguous: bool = False
    clarification_reason: Optional[str] = None
    suggested_clarifications: List[str] = Field(default_factory=list)


class QueryResultFact(BaseModel):
    fact_id: str
    category: str
    column_name: Optional[str] = None
    metric_name: str
    value: Any
    formatted_statement: str


class PrimaryMetric(BaseModel):
    label: str
    value: Any
    formatted: str


class AnalyticalCalculationResult(BaseModel):
    plan_id: str
    success: bool = True
    direct_summary: str = ""
    primary_metric: Optional[PrimaryMetric] = None
    calculation_method: str = ""
    columns_used: List[str] = Field(default_factory=list)
    filters_applied: List[Dict[str, Any]] = Field(default_factory=list)
    tabular_data: List[Dict[str, Any]] = Field(default_factory=list)
    chart: Optional[ChartConfig] = None
    grounded_facts: List[QueryResultFact] = Field(default_factory=list)
    limitations_and_warnings: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class AskDataRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Natural language question")
    include_chart: bool = Field(default=True, description="Whether to generate Plotly chart when applicable")


class ChatMessage(BaseModel):
    message_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str
    dataset_id: str
    snapshot_hash: str
    direct_answer: Optional[str] = None
    primary_metric: Optional[PrimaryMetric] = None
    calculation_method: Optional[str] = None
    columns_used: List[str] = Field(default_factory=list)
    filters_applied: List[Dict[str, Any]] = Field(default_factory=list)
    tabular_data: List[Dict[str, Any]] = Field(default_factory=list)
    chart: Optional[ChartConfig] = None
    grounded_facts: List[QueryResultFact] = Field(default_factory=list)
    limitations_and_warnings: List[str] = Field(default_factory=list)
    is_ambiguous: bool = False
    clarification_prompt: Optional[str] = None
    suggested_follow_ups: List[str] = Field(default_factory=list)
    mode: Literal["ai_generated", "statistical_fallback"] = "ai_generated"
    provider: str = "gemini"
    model: str = "gemini-3.8-flash"


class AskDataResponse(BaseModel):
    message_id: str
    dataset_id: str
    snapshot_hash: str
    question: str
    direct_answer: str
    primary_metric: Optional[PrimaryMetric] = None
    calculation_method: str
    columns_used: List[str] = Field(default_factory=list)
    filters_applied: List[Dict[str, Any]] = Field(default_factory=list)
    tabular_data: List[Dict[str, Any]] = Field(default_factory=list)
    chart: Optional[ChartConfig] = None
    grounded_facts: List[QueryResultFact] = Field(default_factory=list)
    limitations_and_warnings: List[str] = Field(default_factory=list)
    is_ambiguous: bool = False
    clarification_prompt: Optional[str] = None
    suggested_follow_ups: List[str] = Field(default_factory=list)
    mode: Literal["ai_generated", "statistical_fallback"]
    provider: str
    model: str
    created_at: str


class ConversationHistoryResponse(BaseModel):
    dataset_id: str
    snapshot_hash: str
    messages: List[ChatMessage]
    total_messages: int
    is_snapshot_synced: bool = True
    notice: Optional[str] = None


class SuggestedPromptsResponse(BaseModel):
    dataset_id: str
    prompts: List[str]

