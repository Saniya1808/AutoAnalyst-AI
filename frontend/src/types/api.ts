export interface HealthResponse {
  status: string
  service: string
  version: string
  environment: string
}

export type BackendConnectionStatus = 'checking' | 'online' | 'offline'

export interface ApiState<T> {
  data: T | null
  status: BackendConnectionStatus
  error: string | null
  lastChecked: Date | null
}
