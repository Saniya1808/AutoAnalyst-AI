import type { ChartConfig } from './dashboard'

export interface QueryResultFact {
  fact_id: string
  category: string
  column_name?: string | null
  metric_name: string
  value: unknown
  formatted_statement: string
}

export interface PrimaryMetric {
  label: string
  value: unknown
  formatted: string
}

export interface ChatMessage {
  message_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  dataset_id: string
  snapshot_hash: string
  direct_answer?: string | null
  primary_metric?: PrimaryMetric | null
  calculation_method?: string | null
  columns_used: string[]
  filters_applied: Array<Record<string, unknown>>
  tabular_data: Array<Record<string, unknown>>
  chart?: ChartConfig | null
  grounded_facts: QueryResultFact[]
  limitations_and_warnings: string[]
  is_ambiguous?: boolean
  clarification_prompt?: string | null
  suggested_follow_ups: string[]
  mode: 'ai_generated' | 'statistical_fallback'
  provider: string
  model: string
}

export interface AskDataRequest {
  question: string
  include_chart?: boolean
}

export interface AskDataResponse {
  message_id: string
  dataset_id: string
  snapshot_hash: string
  question: string
  direct_answer: string
  primary_metric?: PrimaryMetric | null
  calculation_method: string
  columns_used: string[]
  filters_applied: Array<Record<string, unknown>>
  tabular_data: Array<Record<string, unknown>>
  chart?: ChartConfig | null
  grounded_facts: QueryResultFact[]
  limitations_and_warnings: string[]
  is_ambiguous: boolean
  clarification_prompt?: string | null
  suggested_follow_ups: string[]
  mode: 'ai_generated' | 'statistical_fallback'
  provider: string
  model: string
  created_at: string
}

export interface ConversationHistoryResponse {
  dataset_id: string
  snapshot_hash: string
  messages: ChatMessage[]
  total_messages: number
  is_snapshot_synced: boolean
  notice?: string | null
}

export interface SuggestedPromptsResponse {
  dataset_id: string
  prompts: string[]
}
