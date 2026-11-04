import type { HealthResponse } from '../types/api'
import type { DatasetUnderstandingResponse } from '../types/ai'
import type { AutomatedInsightsResponse } from '../types/insights'
import type {
  AskDataRequest,
  AskDataResponse,
  ConversationHistoryResponse,
  SuggestedPromptsResponse,
} from '../types/ask'
import type {
  CleaningApplyRequest,
  CleaningApplyResponse,
  CleaningPreviewRequest,
  CleaningPreviewResponse,
  DataQualityProfile,
  ResetResponse,
  TransformationHistoryResponse,
  UndoResponse,
} from '../types/cleaning'
import type {
  ChartConfig,
  CustomChartRequest,
  DashboardResponse,
  DrillDownRequest,
  DrillDownResponse,
  FilterDashboardRequest,
} from '../types/dashboard'
import type {
  DatasetDeleteResponse,
  DatasetDetail,
  DatasetListResponse,
  DatasetPreview,
} from '../types/dataset'
import type {
  ExecutiveReportData,
  ReportConfigRequest,
  ReportExportResult,
} from '../types/reports'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'

const SESSION_STORAGE_KEY = 'autoanalyst_session_id'

/**
 * Retrieve or generate a cryptographically isolated anonymous visitor session ID.
 * Persisted in browser localStorage to scope and protect user uploads.
 */
export function getOrCreateSessionId(): string {
  try {
    let sessionId = localStorage.getItem(SESSION_STORAGE_KEY)
    if (!sessionId) {
      sessionId = `sess_${typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID().replace(/-/g, '') : Math.random().toString(36).substring(2) + Date.now().toString(36)}`
      localStorage.setItem(SESSION_STORAGE_KEY, sessionId)
    }
    return sessionId
  } catch {
    return 'sess_fallback_anonymous'
  }
}

/**
 * Return headers containing the visitor's anonymous session ID.
 */
export function getSessionHeaders(): Record<string, string> {
  return {
    'X-Session-ID': getOrCreateSessionId(),
  }
}

/**
 * Fetch health status from FastAPI backend
 */
export async function getBackendHealth(timeoutMs = 5000): Promise<HealthResponse> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal: controller.signal,
    })

    if (!response.ok) {
      throw new Error(`Backend responded with status HTTP ${response.status}`)
    }

    const data = (await response.json()) as HealthResponse
    return data
  } catch (error: unknown) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Connection timed out while reaching backend API')
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

/**
 * Upload a dataset file (.csv, .xlsx, .xls) and receive full Pandas profiling
 */
export async function uploadDataset(file: File): Promise<DatasetDetail> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/datasets/upload`, {
    method: 'POST',
    headers: {
      ...getSessionHeaders(),
    },
    body: formData,
  })

  if (!response.ok) {
    let errorMessage = `Upload failed (HTTP ${response.status})`
    try {
      const errorJson = await response.json()
      if (errorJson && errorJson.detail) {
        errorMessage =
          typeof errorJson.detail === 'string'
            ? errorJson.detail
            : JSON.stringify(errorJson.detail)
      }
    } catch {
      // Use fallback error message
    }
    throw new Error(errorMessage)
  }

  return (await response.json()) as DatasetDetail
}

/**
 * List all uploaded datasets
 */
export async function listDatasets(): Promise<DatasetListResponse> {
  const response = await fetch(`${API_BASE_URL}/datasets`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      ...getSessionHeaders(),
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to list datasets (HTTP ${response.status})`)
  }

  return (await response.json()) as DatasetListResponse
}

/**
 * Fetch full profile and preview for a dataset by ID
 */
export async function getDataset(id: string): Promise<DatasetDetail> {
  const response = await fetch(`${API_BASE_URL}/datasets/${encodeURIComponent(id)}`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      ...getSessionHeaders(),
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch dataset (HTTP ${response.status})`)
  }

  return (await response.json()) as DatasetDetail
}

/**
 * Fetch paginated preview rows for a dataset
 */
export async function getDatasetPreview(
  id: string,
  offset = 0,
  limit = 50
): Promise<DatasetPreview> {
  const url = `${API_BASE_URL}/datasets/${encodeURIComponent(id)}/preview?offset=${offset}&limit=${limit}`
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      ...getSessionHeaders(),
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch preview rows (HTTP ${response.status})`)
  }

  return (await response.json()) as DatasetPreview
}

/**
 * Delete a dataset
 */
export async function deleteDataset(id: string): Promise<DatasetDeleteResponse> {
  const response = await fetch(`${API_BASE_URL}/datasets/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: {
      Accept: 'application/json',
      ...getSessionHeaders(),
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to delete dataset (HTTP ${response.status})`)
  }

  return (await response.json()) as DatasetDeleteResponse
}

/**
 * Fetch automatic KPI dashboard and recommended charts for a dataset
 */
export async function getDatasetDashboard(
  datasetId: string,
  selectedColumn?: string
): Promise<DashboardResponse> {
  const query = selectedColumn ? `?selected_column=${encodeURIComponent(selectedColumn)}` : ''
  const response = await fetch(`${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/dashboard${query}`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      ...getSessionHeaders(),
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch dashboard (HTTP ${response.status})`)
  }

  return (await response.json()) as DashboardResponse
}

/**
 * Fetch recommended charts for a dataset
 */
export async function getChartRecommendations(datasetId: string): Promise<ChartConfig[]> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/chart-recommendations`,
    {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch chart recommendations (HTTP ${response.status})`)
  }

  return (await response.json()) as ChartConfig[]
}

/**
 * Dynamically generate custom chart based on user explorer configuration
 */
export async function generateCustomChart(
  datasetId: string,
  req: CustomChartRequest
): Promise<ChartConfig> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/charts/generate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
      body: JSON.stringify(req),
    }
  )

  if (!response.ok) {
    let msg = `Failed to generate chart (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as ChartConfig
}

/**
 * Apply filters to dashboard and receive updated KPIs and charts
 */
export async function filterDashboard(
  datasetId: string,
  req: FilterDashboardRequest
): Promise<DashboardResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/dashboard/filter`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
      body: JSON.stringify(req),
    }
  )

  if (!response.ok) {
    let msg = `Failed to filter dashboard (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as DashboardResponse
}

/**
 * Fetch category drill-down details
 */
export async function getCategoryDrilldown(
  datasetId: string,
  req: DrillDownRequest
): Promise<DrillDownResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/dashboard/drilldown`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
      body: JSON.stringify(req),
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch drill-down details (HTTP ${response.status})`)
  }

  return (await response.json()) as DrillDownResponse
}

/**
 * Fetch comprehensive data quality profile for cleaning
 */
export async function getCleaningProfile(datasetId: string): Promise<DataQualityProfile> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/cleaning/profile`,
    {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    let msg = `Failed to fetch cleaning profile (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as DataQualityProfile
}

/**
 * Preview a cleaning operation without persisting changes
 */
export async function previewCleaningOperation(
  datasetId: string,
  req: CleaningPreviewRequest
): Promise<CleaningPreviewResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/cleaning/preview`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
      body: JSON.stringify(req),
    }
  )

  if (!response.ok) {
    let msg = `Failed to preview cleaning operation (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as CleaningPreviewResponse
}

/**
 * Apply a cleaning transformation, snapshot state, and update cleaned dataset
 */
export async function applyCleaningOperation(
  datasetId: string,
  req: CleaningApplyRequest
): Promise<CleaningApplyResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/cleaning/apply`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
      body: JSON.stringify(req),
    }
  )

  if (!response.ok) {
    let msg = `Failed to apply cleaning transformation (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as CleaningApplyResponse
}

/**
 * Fetch transformation audit history for a dataset
 */
export async function getCleaningHistory(
  datasetId: string
): Promise<TransformationHistoryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/cleaning/history`,
    {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch transformation history (HTTP ${response.status})`)
  }

  return (await response.json()) as TransformationHistoryResponse
}

/**
 * Undo the most recent cleaning transformation
 */
export async function undoCleaningOperation(datasetId: string): Promise<UndoResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/cleaning/undo`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    let msg = `Failed to undo transformation (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as UndoResponse
}

/**
 * Reset all transformations and restore pristine original dataset
 */
export async function resetCleaningDataset(datasetId: string): Promise<ResetResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/cleaning/reset`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    let msg = `Failed to reset dataset (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as ResetResponse
}

/**
 * Fetch AI-powered dataset understanding (or statistical fallback)
 */
export async function getDatasetUnderstanding(
  datasetId: string
): Promise<DatasetUnderstandingResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/understanding`,
    {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    let msg = `Failed to get dataset understanding (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as DatasetUnderstandingResponse
}

/**
 * Force refresh AI dataset understanding (bypassing cache)
 */
export async function refreshDatasetUnderstanding(
  datasetId: string
): Promise<DatasetUnderstandingResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/understanding/refresh`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    let msg = `Failed to refresh dataset understanding (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as DatasetUnderstandingResponse
}

/**
 * Ask a natural language question about the dataset
 */
export async function askDatasetQuestion(
  datasetId: string,
  request: AskDataRequest
): Promise<AskDataResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/ask`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
      body: JSON.stringify(request),
    }
  )

  if (!response.ok) {
    let msg = `Failed to ask dataset question (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as AskDataResponse
}

/**
 * Get conversation history for a dataset
 */
export async function getConversationHistory(
  datasetId: string
): Promise<ConversationHistoryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/conversation`,
    {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    let msg = `Failed to get conversation history (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as ConversationHistoryResponse
}

/**
 * Clear conversation history for a dataset
 */
export async function clearConversation(
  datasetId: string
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/conversation`,
    {
      method: 'DELETE',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    let msg = `Failed to clear conversation (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as { success: boolean; message: string }
}

/**
 * Get suggested analytical questions based on dataset schema
 */
export async function getSuggestedQuestions(
  datasetId: string
): Promise<SuggestedPromptsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/suggested-questions`,
    {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    let msg = `Failed to get suggested questions (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as SuggestedPromptsResponse
}

/**
 * Get automated dataset insights, best/worst benchmarks, and actionable recommendations.
 */
export async function getAutomatedInsights(
  datasetId: string,
  params?: { date_col?: string; metric_col?: string; granularity?: string }
): Promise<AutomatedInsightsResponse> {
  const queryParams = new URLSearchParams()
  if (params?.date_col) queryParams.set('date_col', params.date_col)
  if (params?.metric_col) queryParams.set('metric_col', params.metric_col)
  if (params?.granularity) queryParams.set('granularity', params.granularity)
  const qs = queryParams.toString() ? `?${queryParams.toString()}` : ''

  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/insights${qs}`,
    {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    let msg = `Failed to get automated insights (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as AutomatedInsightsResponse
}

/**
 * Force refresh automated dataset insights, recalculating and bypassing cache.
 */
export async function refreshAutomatedInsights(
  datasetId: string,
  params?: { date_col?: string; metric_col?: string; granularity?: string }
): Promise<AutomatedInsightsResponse> {
  const queryParams = new URLSearchParams()
  if (params?.date_col) queryParams.set('date_col', params.date_col)
  if (params?.metric_col) queryParams.set('metric_col', params.metric_col)
  if (params?.granularity) queryParams.set('granularity', params.granularity)
  const qs = queryParams.toString() ? `?${queryParams.toString()}` : ''

  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/insights/refresh${qs}`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
    }
  )

  if (!response.ok) {
    let msg = `Failed to refresh automated insights (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as AutomatedInsightsResponse
}

/**
 * Helper to safely extract filename from Content-Disposition header with fallback.
 */
function extractDownloadFilename(header: string | null, fallback: string): string {
  if (!header) return fallback
  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1].trim())
    } catch {
      return utf8Match[1].trim()
    }
  }
  const match = header.match(/filename=["']?([^"';]+)["']?/i)
  if (match && match[1]) {
    return match[1].trim()
  }
  return fallback
}

/**
 * Trigger client-side file download from a Blob and safely clean up object URL.
 * Defers URL revocation to prevent Chromium download shelf ERR_FAILED race conditions.
 */
export function triggerFileDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.style.display = 'none'
  a.href = url
  a.download = filename
  a.rel = 'noopener noreferrer'
  document.body.appendChild(a)
  a.click()

  // Defer cleanup so Chromium download manager completely finishes
  // writing to disk and registering the file association in the downloads shelf.
  setTimeout(() => {
    try {
      if (document.body.contains(a)) {
        document.body.removeChild(a)
      }
      window.URL.revokeObjectURL(url)
    } catch {
      // Safe fallback
    }
  }, 60000)
}

/**
 * Generate full Executive Intelligence Report preview data from backend.
 * POST /api/v1/datasets/{dataset_id}/reports/generate
 */
export async function generateExecutiveReport(
  datasetId: string,
  config?: ReportConfigRequest
): Promise<ExecutiveReportData> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/reports/generate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...getSessionHeaders(),
      },
      body: JSON.stringify(config || {}),
    }
  )

  if (!response.ok) {
    let msg = `Failed to generate executive report (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) {
        msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
      }
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  return (await response.json()) as ExecutiveReportData
}

/**
 * Export publication-grade Executive PDF report.
 * POST /api/v1/datasets/{dataset_id}/reports/export/pdf
 */
export async function exportReportPdf(
  datasetId: string,
  config?: ReportConfigRequest
): Promise<ReportExportResult> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/reports/export/pdf`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/pdf',
        ...getSessionHeaders(),
      },
      body: JSON.stringify(config || {}),
    }
  )

  if (!response.ok) {
    let msg = `Failed to export PDF report (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) {
        msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
      }
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  const rawBlob = await response.blob()
  const blob = new Blob([rawBlob], { type: 'application/pdf' })
  const contentDisp = response.headers.get('content-disposition')
  let filename = extractDownloadFilename(contentDisp, `Executive_Report_${datasetId}.pdf`)
  if (!filename.toLowerCase().endsWith('.pdf')) {
    filename = `${filename}.pdf`
  }

  return { blob, filename }
}

/**
 * Export 8-worksheet styled executive Excel workbook (.xlsx).
 * POST /api/v1/datasets/{dataset_id}/reports/export/excel
 */
export async function exportReportExcel(
  datasetId: string,
  config?: ReportConfigRequest
): Promise<ReportExportResult> {
  const response = await fetch(
    `${API_BASE_URL}/datasets/${encodeURIComponent(datasetId)}/reports/export/excel`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ...getSessionHeaders(),
      },
      body: JSON.stringify(config || {}),
    }
  )

  if (!response.ok) {
    let msg = `Failed to export Excel report (HTTP ${response.status})`
    try {
      const err = await response.json()
      if (err?.detail) {
        msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
      }
    } catch {
      // fallback
    }
    throw new Error(msg)
  }

  const rawBlob = await response.blob()
  const blob = new Blob([rawBlob], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const contentDisp = response.headers.get('content-disposition')
  let filename = extractDownloadFilename(contentDisp, `Executive_Report_${datasetId}.xlsx`)
  if (!filename.toLowerCase().endsWith('.xlsx')) {
    filename = `${filename}.xlsx`
  }

  return { blob, filename }
}

export { API_BASE_URL }
