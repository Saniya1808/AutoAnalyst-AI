from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ComputedFact(BaseModel):
    fact_id: str = Field(..., description="Unique stable identifier for the fact")
    category: str = Field(..., description="dimension, quality, numeric_statistic, categorical_distribution, correlation")
    column_name: Optional[str] = None
    metric_name: str
    value: Any = Field(..., description="Calculated actual value from Pandas")
    formatted_statement: str


class TargetVariableDetection(BaseModel):
    column_name: str
    confidence: str = Field(default="medium", description="high, medium, low")
    reasoning: str
    referenced_fact_ids: List[str] = Field(default_factory=list)


class DatasetOverviewAI(BaseModel):
    domain: str = Field(..., description="Inferred business or scientific domain")
    likely_purpose: str = Field(..., description="Primary analytical purpose of this dataset")
    executive_summary: str = Field(..., description="Professional natural-language summary")
    detected_target_variable: Optional[TargetVariableDetection] = None
    referenced_fact_ids: List[str] = Field(default_factory=list)


class ColumnUnderstandingAI(BaseModel):
    name: str
    semantic_type: str
    business_meaning: str
    is_key_feature: bool = False
    is_identifier: bool = False
    data_quality_note: Optional[str] = None
    referenced_fact_ids: List[str] = Field(default_factory=list)


class ObservationAI(BaseModel):
    observation_type: str = Field(..., description="observed_fact, interpretation, hypothesis")
    statement: str
    business_implication: str
    referenced_fact_ids: List[str] = Field(default_factory=list)
    is_verified_fact: bool = False


class RelationshipAI(BaseModel):
    primary_column: str
    secondary_column: str
    relationship_description: str
    analytical_type: str = Field(default="comparison", description="correlation, segmentation, temporal_trend, comparison")
    referenced_fact_ids: List[str] = Field(default_factory=list)


class SuggestedKPI(BaseModel):
    name: str
    calculation: str
    purpose: str
    business_value: str
    target_column: Optional[str] = None


class RecommendedChartAI(BaseModel):
    chart_type: str = Field(..., description="bar, line, scatter, box, histogram, pie")
    title: str
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    aggregation: Optional[str] = None
    reason: str


class AnalyticalInsightsAI(BaseModel):
    key_observations: List[ObservationAI] = Field(default_factory=list)
    potential_relationships: List[RelationshipAI] = Field(default_factory=list)
    business_relevance: str


class SuggestedAnalysisAI(BaseModel):
    suggested_kpis: List[SuggestedKPI] = Field(default_factory=list)
    recommended_charts: List[RecommendedChartAI] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)


class DatasetUnderstandingResponse(BaseModel):
    dataset_id: str
    filename: str
    is_cleaned: bool = False
    version: int = 0
    snapshot_hash: str
    mode: str = Field(..., description="ai_generated or statistical_fallback")
    provider: str
    model: str
    generated_at: str
    is_cached: bool = False
    computed_facts: Dict[str, ComputedFact] = Field(default_factory=dict)
    overview: DatasetOverviewAI
    columns: List[ColumnUnderstandingAI] = Field(default_factory=list)
    analytical_insights: AnalyticalInsightsAI
    suggested_analysis: SuggestedAnalysisAI
    validation_warnings: List[str] = Field(default_factory=list)
    error_detail: Optional[str] = None
    can_retry: bool = False

