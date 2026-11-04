import type { HealthResponse } from '../types/api'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'

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
        'Accept': 'application/json',
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

export { API_BASE_URL }
