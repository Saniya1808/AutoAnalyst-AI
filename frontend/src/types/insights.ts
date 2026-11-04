import type { ChartConfig } from './dashboard'

export type SemanticRole =
  | 'identifier'
  | 'numerical_measure'
  | 'categorical_dimension'
  | 'entity_name'
  | 'date_time'
  | 'url_media'
  | 'free_text'

export interface ColumnClassification {
  name: string
  semantic_role: SemanticRole
  inferred_type: string
  unique_count: number
  null_count: number
  is_usable_for_metrics: boolean
  is_usable_for_grouping: boolean
  classification_reason: string
}

export interface KeyFinding {
  finding_id: string
  title: string
  description: string
  significance_score: number
  importance: 'high' | 'medium' | 'notable'
  category: 'distribution' | 'correlation' | 'trend' | 'imbalance' | 'quality' | 'benchmark'
  columns_involved: string[]
  referenced_fact_ids: string[]
  metric_formatted?: string | null
}

export interface CategoryPerformer {
  category_name: string
  metric_value: number
  formatted_value: string
  delta_vs_average_pct: number
  sample_size: number
  is_statistically_reliable: boolean
}

export interface BestWorstAnalysis {
  dimension_column: string
  metric_column?: string | null
  aggregation: string
  dataset_average: number
  formatted_average: string
  best_performer: CategoryPerformer
  worst_performer: CategoryPerformer
  ranked_performers: CategoryPerformer[]
  chart?: ChartConfig | null
  explanation: string
  referenced_fact_ids: string[]
}

export interface AnomalyPattern {
  anomaly_id: string
  anomaly_type:
    | 'numerical_outlier'
    | 'rare_category'
    | 'missing_concentration'
    | 'zero_inflation'
    | 'invariant_column'
    | 'extreme_skewness'
  severity: 'critical' | 'warning' | 'info'
  column_name: string
  description: string
  metric_evidence: Record<string, unknown>
  referenced_fact_ids: string[]
}

export interface BusinessRecommendation {
  recommendation_id: string
  title: string
  action_statement: string
  expected_impact: string
  priority: 'high' | 'medium' | 'low'
  category: 'data_quality' | 'operational' | 'commercial' | 'risk' | 'exploratory'
  is_hypothesis: boolean
  referenced_fact_ids: string[]
}

export interface GroundedFact {
  fact_id: string
  category: string
  column_name?: string | null
  metric_name: string
  value: unknown
  formatted_statement: string
}

// =========================================================================
// PHASE 4.4 TEMPORAL TREND & ANOMALY INTELLIGENCE TYPES
// =========================================================================

export type DateGranularity = 'year' | 'quarter' | 'month' | 'week' | 'day'
export type TrendDirection = 'increasing' | 'decreasing' | 'stable' | 'fluctuating'
export type StatisticalEvidence = 'statistically_supported' | 'exploratory_pattern' | 'insufficient_sample'
export type BusinessMagnitude = 'material' | 'moderate' | 'immaterial'
export type TemporalAnomalyType = 'sudden_spike' | 'sudden_drop' | 'deterministic_step_anomaly'
export type SeasonalityStatus = 'statistically_supported' | 'exploratory_pattern' | 'insufficient_duration' | 'no_seasonality_detected'

export interface DateMetricCombination {
  combination_id: string
  date_column: string
  metric_column: string
  granularity: DateGranularity
  total_periods: number
  is_default: boolean
  display_label: string
}

export interface PeriodDataPoint {
  period_label: string
  timestamp?: string | null
  value: number
  formatted_value: string
  period_over_period_pct?: number | null
  is_partial_period: boolean
  temporal_completeness_pct: number
  is_anomaly: boolean
  anomaly_severity?: 'critical' | 'warning' | 'info' | null
}

export interface TrendAnalysis {
  trend_id: string
  date_column: string
  metric_column: string
  granularity: DateGranularity
  direction: TrendDirection
  statistical_evidence: StatisticalEvidence
  business_magnitude: BusinessMagnitude
  p_value?: number | null
  p_value_fdr_adjusted?: number | null
  durbin_watson_stat?: number | null
  trend_strength_r2: number
  absolute_change: number
  formatted_absolute_change: string
  conventional_growth_pct?: number | null
  range_normalized_shift_pct?: number | null
  starting_baseline: number
  ending_baseline: number
  peak_period: string
  peak_value: number
  trough_period: string
  trough_value: number
  data_points: PeriodDataPoint[]
  chart?: ChartConfig | null
  explanation: string
  referenced_fact_ids: string[]
}

export interface TemporalAnomaly {
  anomaly_id: string
  period_label: string
  timestamp?: string | null
  anomaly_type: TemporalAnomalyType
  severity: 'critical' | 'warning' | 'info'
  observed_value: number
  formatted_observed_value: string
  baseline_reference: number
  formatted_baseline_reference: string
  absolute_diff: number
  period_over_period_pct?: number | null
  robust_z_score: number
  description: string
  detection_method: string
  referenced_fact_ids: string[]
}

export interface SeasonalPattern {
  period_name: string
  average_value: number
  formatted_value: string
  delta_vs_overall_avg_pct: number
  sample_occurrences: number
}

export interface SeasonalityAnalysis {
  is_detected: boolean
  status: SeasonalityStatus
  cycle_type?: 'day_of_week' | 'month_of_year' | null
  anova_f_stat?: number | null
  anova_p_value?: number | null
  kruskal_p_value?: number | null
  peak_season?: string | null
  trough_season?: string | null
  patterns: SeasonalPattern[]
  chart?: ChartConfig | null
  explanation: string
  referenced_fact_ids: string[]
}

export interface AutomatedInsightsResponse {
  dataset_id: string
  dataset_name: string
  snapshot_hash: string
  mode: 'ai_generated' | 'statistical_fallback'
  provider: string
  model: string
  generated_at: string
  is_cached: boolean
  executive_summary: string
  health_score: number
  column_classifications: ColumnClassification[]
  key_findings: KeyFinding[]
  best_worst_analyses: BestWorstAnalysis[]
  anomalies_and_patterns: AnomalyPattern[]
  recommendations: BusinessRecommendation[]
  grounded_facts: GroundedFact[]
  limitations: string[]

  // Phase 4.4 Additions
  has_temporal_data: boolean
  available_combinations: DateMetricCombination[]
  trends: TrendAnalysis[]
  temporal_anomalies: TemporalAnomaly[]
  seasonality?: SeasonalityAnalysis | null
}
