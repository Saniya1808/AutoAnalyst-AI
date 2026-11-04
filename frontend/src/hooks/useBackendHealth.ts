import { useState, useEffect, useCallback } from 'react'
import { getBackendHealth } from '../services/api'
import type { HealthResponse, ApiState } from '../types/api'

export function useBackendHealth(pollIntervalMs: number = 30000) {
  const [state, setState] = useState<ApiState<HealthResponse>>({
    data: null,
    status: 'checking',
    error: null,
    lastChecked: null,
  })

  const checkHealth = useCallback(async () => {
    setState((prev) => ({ ...prev, status: 'checking' }))
    try {
      const data = await getBackendHealth()
      setState({
        data,
        status: 'online',
        error: null,
        lastChecked: new Date(),
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown connection error'
      setState({
        data: null,
        status: 'offline',
        error: message,
        lastChecked: new Date(),
      })
    }
  }, [])

  useEffect(() => {
    checkHealth()

    if (pollIntervalMs > 0) {
      const timer = setInterval(checkHealth, pollIntervalMs)
      return () => clearInterval(timer)
    }
  }, [checkHealth, pollIntervalMs])

  return {
    ...state,
    refetch: checkHealth,
  }
}
