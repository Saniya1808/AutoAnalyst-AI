export interface ComputedFact {
  fact_id: string
  category: string
  column_name?: string | null
  metric_name: string
  value: unknown
  formatted_statement: string
}

export interface TargetVariableDetection {
  column_name: string
  confidence: 'high' | 'medium' | 'low'
  reasoning: string
  referenced_fact_ids: string[]
}

export interface DatasetOverviewAI {
  domain: string
  likely_purpose: string
  executive_summary: string
  detected_target_variable?: TargetVariableDetection | null
  referenced_fact_ids: string[]
}

export interface ColumnUnderstandingAI {
  name: string
  semantic_type: string
  business_meaning: string
  is_key_feature: boolean
  is_identifier: boolean
  data_quality_note?: string | null
  referenced_fact_ids: string[]
}

export interface ObservationAI {
  observation_type: 'observed_fact' | 'interpretation' | 'hypothesis'
  statement: string
  business_implication: string
  referenced_fact_ids: string[]
  is_verified_fact: boolean
}

export interface RelationshipAI {
  primary_column: string
  secondary_column: string
  relationship_description: string
  analytical_type: 'correlation' | 'segmentation' | 'temporal_trend' | 'comparison' | string
  referenced_fact_ids: string[]
}

export interface SuggestedKPI {
  name: string
  calculation: string
  purpose: string
  business_value: string
  target_column?: string | null
}

export interface RecommendedChartAI {
  chart_type: 'bar' | 'line' | 'scatter' | 'box' | 'histogram' | 'pie' | string
  title: string
  x_column?: string | null
  y_column?: string | null
  aggregation?: string | null
  reason: string
}

export interface AnalyticalInsightsAI {
  key_observations: ObservationAI[]
  potential_relationships: RelationshipAI[]
  business_relevance: string
}

export interface SuggestedAnalysisAI {
  suggested_kpis: SuggestedKPI[]
  recommended_charts: RecommendedChartAI[]
  suggested_questions: string[]
}

export interface DatasetUnderstandingResponse {
  dataset_id: string
  filename: string
  is_cleaned: boolean
  version: number
  snapshot_hash: string
  mode: 'ai_generated' | 'statistical_fallback'
  provider: string
  model: string
  generated_at: string
  is_cached: boolean
  computed_facts: Record<string, ComputedFact>
  overview: DatasetOverviewAI
  columns: ColumnUnderstandingAI[]
  analytical_insights: AnalyticalInsightsAI
  suggested_analysis: SuggestedAnalysisAI
  validation_warnings: string[]
}

