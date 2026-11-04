from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.models.ask_data import QueryResultFact
from app.models.dashboard import ChartConfig


SemanticRole = Literal[
    "identifier",
    "numerical_measure",
    "categorical_dimension",
    "entity_name",
    "date_time",
    "url_media",
    "free_text",
]


class ColumnClassification(BaseModel):
    name: str = Field(..., description="Column name")
    semantic_role: SemanticRole = Field(..., description="Inferred semantic analytical role")
    inferred_type: str = Field(..., description="Data type: integer, float, string, boolean, datetime")
    unique_count: int = Field(..., description="Number of distinct non-null values")
    null_count: int = Field(..., description="Number of null/missing cells")
    is_usable_for_metrics: bool = Field(default=False, description="Whether column is suitable for business aggregations")
    is_usable_for_grouping: bool = Field(default=False, description="Whether column is suitable as a categorical dimension")
    classification_reason: str = Field(default="", description="Reasoning for assigned semantic role")


class KeyFinding(BaseModel):
    finding_id: str
    title: str
    description: str
    significance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Analytical significance rank")
    importance: Literal["high", "medium", "notable"] = "medium"
    category: Literal["distribution", "correlation", "trend", "imbalance", "quality", "benchmark"]
    columns_involved: List[str] = Field(default_factory=list)
    referenced_fact_ids: List[str] = Field(default_factory=list)
    metric_formatted: Optional[str] = None


class CategoryPerformer(BaseModel):
    category_name: str
    metric_value: float
    formatted_value: str
    delta_vs_average_pct: float = Field(..., description="Percentage difference vs dataset average")
    sample_size: int = Field(..., description="Number of records in this category")
    is_statistically_reliable: bool = Field(default=True, description="False if sample size is too small (n < 5)")


class BestWorstAnalysis(BaseModel):
    dimension_column: str
    metric_column: Optional[str] = None
    aggregation: str = "mean"
    dataset_average: float
    formatted_average: str
    best_performer: CategoryPerformer
    worst_performer: CategoryPerformer
    ranked_performers: List[CategoryPerformer] = Field(default_factory=list)
    chart: Optional[ChartConfig] = None
    explanation: str
    referenced_fact_ids: List[str] = Field(default_factory=list)


class AnomalyPattern(BaseModel):
    anomaly_id: str
    anomaly_type: Literal[
        "numerical_outlier",
        "rare_category",
        "missing_concentration",
        "zero_inflation",
        "invariant_column",
        "extreme_skewness",
    ]
    severity: Literal["critical", "warning", "info"] = "warning"
    column_name: str
    description: str
    metric_evidence: Dict[str, Any] = Field(default_factory=dict)
    referenced_fact_ids: List[str] = Field(default_factory=list)


class BusinessRecommendation(BaseModel):
    recommendation_id: str
    title: str
    action_statement: str
    expected_impact: str
    priority: Literal["high", "medium", "low"] = "medium"
    category: Literal["data_quality", "operational", "commercial", "risk", "exploratory"]
    is_hypothesis: bool = Field(default=False, description="True if based on analytical assumption rather than pure observed fact")
    referenced_fact_ids: List[str] = Field(default_factory=list)


# =============================================================================
# Phase 4.4: Trend & Anomaly Intelligence Models
# =============================================================================

TrendDirection = Literal["increasing", "decreasing", "stable", "fluctuating"]
StatisticalEvidence = Literal["statistically_supported", "weak_evidence", "inconclusive", "insufficient_sample"]
BusinessMagnitude = Literal["material", "moderate", "immaterial"]
DateGranularity = Literal["year", "quarter", "month", "week", "day"]
TemporalAnomalyType = Literal["sudden_spike", "sudden_drop", "deterministic_step_anomaly"]
SeasonalityStatus = Literal["statistically_supported", "exploratory_pattern", "insufficient_duration", "no_seasonality_detected"]


class DateMetricCombination(BaseModel):
    combination_id: str
    date_column: str
    metric_column: str
    granularity: DateGranularity = "month"
    total_periods: int
    is_default: bool = False
    display_label: str


class PeriodDataPoint(BaseModel):
    period_label: str
    timestamp: Optional[str] = None
    value: float
    formatted_value: str
    period_over_period_pct: Optional[float] = None
    is_partial_period: bool = False
    temporal_completeness_pct: float = 100.0
    is_anomaly: bool = False
    anomaly_severity: Optional[Literal["critical", "warning", "info"]] = None


class TrendAnalysis(BaseModel):
    trend_id: str
    date_column: str
    metric_column: str
    granularity: DateGranularity
    direction: TrendDirection
    statistical_evidence: StatisticalEvidence
    business_magnitude: BusinessMagnitude
    p_value: Optional[float] = None
    p_value_fdr_adjusted: Optional[float] = None
    durbin_watson_stat: Optional[float] = None
    trend_strength_r2: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Strictly separated change metrics
    absolute_change: float
    formatted_absolute_change: str
    conventional_growth_pct: Optional[float] = None      # Populated ONLY when starting baseline > 0
    range_normalized_shift_pct: Optional[float] = None   # Alternative measure when baseline <= 0
    
    start_period: str
    end_period: str
    start_value: float
    end_value: float
    peak_period: str
    peak_value: float
    trough_period: str
    trough_value: float
    data_points: List[PeriodDataPoint] = Field(default_factory=list)
    chart: Optional[ChartConfig] = None
    explanation: str
    referenced_fact_ids: List[str] = Field(default_factory=list)


class TemporalAnomaly(BaseModel):
    anomaly_id: str
    anomaly_type: TemporalAnomalyType
    severity: Literal["critical", "warning", "info"]
    date_column: str
    metric_column: str
    period_label: str
    previous_value: float
    current_value: float
    delta_abs: float
    delta_pct: Optional[float] = None
    detection_method: str
    detection_reason: str
    referenced_fact_ids: List[str] = Field(default_factory=list)


class SeasonalPattern(BaseModel):
    cycle_type: Literal["day_of_week", "month_of_year"]
    period_name: str              # e.g., "Monday", "December"
    average_residual: float
    formatted_average: str
    delta_vs_overall_avg_pct: float
    sample_occurrences: int


class SeasonalityAnalysis(BaseModel):
    is_detected: bool
    status: SeasonalityStatus
    cycle_type: Optional[Literal["day_of_week", "month_of_year"]] = None
    anova_f_stat: Optional[float] = None
    anova_p_value: Optional[float] = None
    kruskal_p_value: Optional[float] = None
    peak_season: Optional[str] = None
    trough_season: Optional[str] = None
    patterns: List[SeasonalPattern] = Field(default_factory=list)
    chart: Optional[ChartConfig] = None
    explanation: str
    referenced_fact_ids: List[str] = Field(default_factory=list)


class AutomatedInsightsResponse(BaseModel):
    dataset_id: str
    dataset_name: str
    snapshot_hash: str
    mode: Literal["ai_generated", "statistical_fallback"]
    provider: str
    model: str
    generated_at: str
    is_cached: bool = False
    executive_summary: str = Field(default="", description="High-level narrative executive briefing")
    health_score: float = Field(default=100.0, description="Overall dataset health and completeness score 0-100")
    column_classifications: List[ColumnClassification] = Field(default_factory=list)
    key_findings: List[KeyFinding] = Field(default_factory=list)
    best_worst_analyses: List[BestWorstAnalysis] = Field(default_factory=list)
    anomalies_and_patterns: List[AnomalyPattern] = Field(default_factory=list)
    recommendations: List[BusinessRecommendation] = Field(default_factory=list)
    grounded_facts: List[QueryResultFact] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    
    # Phase 4.4 Additions
    has_temporal_data: bool = False
    available_combinations: List[DateMetricCombination] = Field(default_factory=list)
    trends: List[TrendAnalysis] = Field(default_factory=list)
    temporal_anomalies: List[TemporalAnomaly] = Field(default_factory=list)
    seasonality: Optional[SeasonalityAnalysis] = None

