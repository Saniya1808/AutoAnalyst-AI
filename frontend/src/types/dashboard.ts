export interface NumericColumnStats {
  column: string
  count: number
  sum: number
  average: number | null
  minimum: number | null
  maximum: number | null
  std: number | null
  zeros_count: number
}

export interface DashboardKPI {
  total_rows: number
  total_columns: number
  total_cells: number
  missing_cells: number
  missing_percentage: number
  duplicate_rows: number
  duplicate_percentage: number
  data_completeness: number
  selected_column?: string | null
  selected_column_stats?: NumericColumnStats | null
}

export interface ChartConfig {
  chart_id: string
  title: string
  chart_type: 'histogram' | 'box' | 'bar' | 'pie' | 'line' | 'scatter'
  x_column?: string | null
  y_column?: string | null
  group_column?: string | null
  aggregation?: 'sum' | 'avg' | 'count' | 'min' | 'max' | null
  description?: string | null
  plotly_data: Record<string, unknown>[]
  plotly_layout: Record<string, unknown>
}

export interface FilterRule {
  column: string
  filter_type: 'categorical' | 'numeric_range' | 'datetime_range'
  selected_values?: string[] | null
  min_val?: number | null
  max_val?: number | null
  start_date?: string | null
  end_date?: string | null
}

export interface FilterOptions {
  categorical_filters: Record<string, string[]>
  numeric_filters: Record<string, { min: number; max: number }>
  datetime_filters: Record<string, { min: string; max: string }>
}

export interface ColumnInfo {
  name: string
  data_type: string
}

export interface DashboardResponse {
  dataset_id: string
  filename: string
  kpis: DashboardKPI
  filter_options: FilterOptions
  active_filters: FilterRule[]
  recommended_charts: ChartConfig[]
  available_columns: ColumnInfo[]
  is_filtered: boolean
  filtered_row_count: number
  total_row_count: number
}

export interface CustomChartRequest {
  chart_type: 'histogram' | 'box' | 'bar' | 'pie' | 'line' | 'scatter'
  x_column?: string | null
  y_column?: string | null
  group_column?: string | null
  aggregation?: 'sum' | 'avg' | 'count' | 'min' | 'max' | null
  filters?: FilterRule[] | null
}

export interface FilterDashboardRequest {
  filters: FilterRule[]
  selected_numeric_column?: string | null
}

export interface DrillDownRequest {
  category_column: string
  category_value: string
  limit?: number
  offset?: number
  filters?: FilterRule[] | null
}

export interface DrillDownResponse {
  category_column: string
  category_value: string
  total_matching_rows: number
  summary_stats: {
    category_column: string
    category_value: string
    matching_rows: number
    percentage_of_total: number
    numeric_metrics?: Record<string, { sum: number; mean: number; min: number; max: number }>
  }
  sample_records: Record<string, unknown>[]
}

