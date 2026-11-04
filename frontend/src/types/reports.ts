/**
 * Executive Report TypeScript interfaces matching backend models in
 * backend/app/models/reports.py.
 *
 * Brand: Powered by Saniya
 * Tagline: Your Autonomous Data Analyst
 */

import type { ChartConfig, DashboardKPI } from './dashboard'
import type { ColumnProfile } from './dataset'
import type { DataQualityProfile } from './cleaning'
import type {
  AnomalyPattern,
  BestWorstAnalysis,
  BusinessRecommendation,
  DateMetricCombination,
  GroundedFact,
  KeyFinding,
  SeasonalityAnalysis,
  TemporalAnomaly,
  TrendAnalysis,
} from './insights'

// =============================================================================
// Report Section Identifiers
// =============================================================================

export type ReportSectionId =
  | 'executive_summary'
  | 'key_kpis'
  | 'key_findings'
  | 'category_benchmarks'
  | 'trends_and_seasonality'
  | 'anomalies_and_risks'
  | 'recommendations'
  | 'data_quality_audit'

export const ALL_REPORT_SECTIONS: ReportSectionId[] = [
  'executive_summary',
  'key_kpis',
  'key_findings',
  'category_benchmarks',
  'trends_and_seasonality',
  'anomalies_and_risks',
  'recommendations',
  'data_quality_audit',
]

export const REPORT_SECTION_META: Record<
  ReportSectionId,
  { label: string; description: string; icon: string }
> = {
  executive_summary: {
    label: 'Executive Summary',
    description: 'Strategic narrative briefing, health score & strategic takeaways',
    icon: 'FileText',
  },
  key_kpis: {
    label: 'Key KPIs & Vital Signs',
    description: 'Executive KPI metrics, volume counts, and data completeness',
    icon: 'Activity',
  },
  key_findings: {
    label: 'Key Findings',
    description: 'Statistical automated findings ranked by significance',
    icon: 'Sparkles',
  },
  category_benchmarks: {
    label: 'Category Benchmarks',
    description: 'Top and bottom performing categories across dimensions',
    icon: 'Award',
  },
  trends_and_seasonality: {
    label: 'Trends & Seasonality',
    description: 'Longitudinal trend direction, OLS/MK tests, and cyclical patterns',
    icon: 'TrendingUp',
  },
  anomalies_and_risks: {
    label: 'Anomalies & Outliers',
    description: 'Categorical anomalies, high skewness, and temporal spikes/drops',
    icon: 'AlertTriangle',
  },
  recommendations: {
    label: 'Recommendations',
    description: 'Actionable business recommendations with empirical/hypothesis tags',
    icon: 'CheckSquare',
  },
  data_quality_audit: {
    label: 'Data Quality Audit',
    description: 'Completeness, uniqueness, validity scores and column health',
    icon: 'ShieldCheck',
  },
}

// =============================================================================
// Report Configuration Request
// =============================================================================

export interface ReportConfigRequest {
  title?: string
  subtitle?: string | null
  selected_sections?: ReportSectionId[]
  include_charts?: boolean
  date_range_start?: string | null
  date_range_end?: string | null
  confidentiality_notice?: string | null
  target_metric_col?: string | null
  target_date_col?: string | null
}

// =============================================================================
// Individual Report Section Models (8 Standardized Sections)
// =============================================================================

export interface ReportExecutiveSummary {
  narrative: string
  mode: 'ai_generated' | 'statistical_fallback'
  provider?: string | null
  model?: string | null
  health_score: number
  key_takeaways: string[]
}

export interface ReportKeyKPIs {
  kpis: DashboardKPI
  health_score: number
  selected_column?: string | null
}

export interface ReportKeyFindings {
  findings: KeyFinding[]
  total_count: number
  high_importance_count: number
}

export interface ReportCategoryBenchmarks {
  benchmarks: BestWorstAnalysis[]
  dimension_count: number
}

export interface ReportTrendsSeasonality {
  has_temporal_data: boolean
  trends: TrendAnalysis[]
  seasonality?: SeasonalityAnalysis | null
  available_combinations: DateMetricCombination[]
}

export interface ReportAnomaliesRisks {
  anomalies: AnomalyPattern[]
  temporal_anomalies: TemporalAnomaly[]
  total_anomaly_count: number
  critical_count: number
  warning_count: number
}

export interface ReportRecommendations {
  recommendations: BusinessRecommendation[]
  total_count: number
  high_priority_count: number
  empirical_facts_count: number
  analytical_hypotheses_count: number
}

export interface ReportDataQualityAudit {
  quality_profile?: DataQualityProfile | null
  overall_quality_score: number
  quality_grade: string
  completeness_score: number
  uniqueness_score: number
  validity_score: number
  column_count: number
  missing_cells: number
  duplicate_rows: number
}

// =============================================================================
// Complete Executive Report Data Model
// =============================================================================

export interface ExecutiveReportData {
  report_id: string
  dataset_id: string
  active_dataset_id: string
  dataset_name: string
  snapshot_hash: string
  is_cleaned: boolean
  cleaning_version: number
  generated_at: string

  // Branding
  brand_name: string
  brand_tagline: string
  brand_attribution: string
  confidentiality_notice?: string | null

  // Configuration applied
  config: ReportConfigRequest
  health_score: number

  // The 8 Standardized Report Sections
  executive_summary?: ReportExecutiveSummary | null
  key_kpis?: ReportKeyKPIs | null
  key_findings?: ReportKeyFindings | null
  category_benchmarks?: ReportCategoryBenchmarks | null
  trends_and_seasonality?: ReportTrendsSeasonality | null
  anomalies_and_risks?: ReportAnomaliesRisks | null
  recommendations?: ReportRecommendations | null
  data_quality_audit?: ReportDataQualityAudit | null

  // Supporting metadata & schemas
  columns: ColumnProfile[]
  charts: ChartConfig[]
  grounded_facts: GroundedFact[]
  limitations: string[]
  date_scoping_limitations: string[]
  section_inclusion_status?: Record<string, boolean>
}

// =============================================================================
// Export Result Helper Types
// =============================================================================

export interface ReportExportResult {
  blob: Blob
  filename: string
}

