export interface DataQualityMetric {
  completeness_score: number
  uniqueness_score: number
  validity_score: number
  overall_quality_score: number
  quality_grade: 'Excellent' | 'Good' | 'Fair' | 'Needs Attention' | string
}

export interface ColumnQualitySummary {
  column_name: string
  position: number
  data_type: string
  total_count: number
  missing_count: number
  missing_percentage: number
  unique_count: number
  is_numeric: boolean
  outliers_iqr_count?: number | null
  outliers_zscore_count?: number | null
}

export interface IQRBoundaries {
  q1: number
  q3: number
  iqr: number
  lower_bound: number
  upper_bound: number
  outlier_count: number
  outlier_percentage: number
}

export interface ZScoreBoundaries {
  mean: number
  std: number
  threshold: number
  lower_bound: number
  upper_bound: number
  outlier_count: number
  outlier_percentage: number
}

export interface DataQualityProfile {
  dataset_id: string
  filename: string
  is_cleaned: boolean
  parent_id?: string | null
  version: number
  total_rows: number
  total_columns: number
  total_cells: number
  total_missing_cells: number
  missing_percentage: number
  duplicate_rows: number
  duplicate_percentage: number
  quality_metrics: DataQualityMetric
  columns: ColumnQualitySummary[]
  outlier_details: Record<string, { iqr?: IQRBoundaries; zscore?: ZScoreBoundaries }>
  original_file_hash?: string | null
}

export interface CleaningPreviewRequest {
  operation_type: 'missing_values' | 'duplicates' | 'type_conversion' | 'outliers'
  column_name?: string
  strategy: string
  parameters?: Record<string, any>
}

export interface CleaningPreviewResponse {
  operation_type: string
  column_name?: string
  strategy: string
  affected_rows: number
  affected_cells: number
  is_valid: boolean
  validation_warnings: string[]
  original_sample: Record<string, any>[]
  cleaned_sample: Record<string, any>[]
  summary: string
}

export interface CleaningApplyRequest {
  operation_type: 'missing_values' | 'duplicates' | 'type_conversion' | 'outliers'
  column_name?: string
  strategy: string
  parameters?: Record<string, any>
}

export interface TransformationStep {
  step_id: number
  version: number
  operation_type: string
  column_name?: string
  strategy: string
  parameters: Record<string, any>
  affected_rows: number
  affected_cells: number
  description: string
  timestamp: string
}

export interface CleaningApplyResponse {
  success: boolean
  message: string
  cleaned_dataset_id: string
  version: number
  step: TransformationStep
  updated_quality: DataQualityProfile
  original_file_hash_verified: boolean
}

export interface TransformationHistoryResponse {
  dataset_id: string
  cleaned_dataset_id?: string | null
  current_version: number
  history: TransformationStep[]
}

export interface UndoResponse {
  success: boolean
  message: string
  current_version: number
  remaining_steps: number
  cleaned_dataset_id: string
  updated_quality: DataQualityProfile
}

export interface ResetResponse {
  success: boolean
  message: string
  original_dataset_id: string
  original_file_hash_verified: boolean
  updated_quality: DataQualityProfile
}

