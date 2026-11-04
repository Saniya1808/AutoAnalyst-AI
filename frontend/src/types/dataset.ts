export interface DatasetOverview {
  id: string
  filename: string
  file_size_bytes: number
  file_type: string
  row_count: number
  column_count: number
  total_cells: number
  missing_cells: number
  missing_percentage: number
  duplicate_rows: number
  duplicate_percentage: number
  memory_usage_bytes: number
  memory_usage_human: string
  uploaded_at: string
  is_cleaned?: boolean
  parent_id?: string | null
  version?: number
  session_id?: string | null
  is_sample?: boolean
}

export type SemanticDataType = 'integer' | 'float' | 'string' | 'boolean' | 'datetime'

export interface ColumnTopValue {
  value: string
  count: number
}

export interface ColumnProfile {
  name: string
  position: number
  data_type: SemanticDataType
  raw_dtype: string
  non_null_count: number
  null_count: number
  null_percentage: number
  unique_count: number
  is_unique: boolean
  sample_values: unknown[]
  min?: number | null
  max?: number | null
  mean?: number | null
  std?: number | null
  median?: number | null
  q25?: number | null
  q75?: number | null
  zeros_count?: number | null
  negative_count?: number | null
  top_values?: ColumnTopValue[] | null
  min_date?: string | null
  max_date?: string | null
}

export interface DatasetPreview {
  columns: string[]
  column_types: Record<string, string>
  rows: Record<string, unknown>[]
  total_rows: number
  preview_rows_count: number
  offset: number
  limit: number
}

export interface DatasetDetail {
  overview: DatasetOverview
  columns: ColumnProfile[]
  preview: DatasetPreview
}

export interface DatasetListResponse {
  datasets: DatasetOverview[]
  total_datasets: number
  total_rows_all: number
  total_columns_all: number
}

export interface DatasetDeleteResponse {
  message: string
  id: string
  success: boolean
}

