import { apiClient } from './axios'

export interface HealthCheckItem {
  status: 'ok' | 'error'
  message: string
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  checks: {
    api: HealthCheckItem
    onlyoffice: HealthCheckItem
    database: HealthCheckItem
    tesseract: HealthCheckItem
  }
}

export const healthApi = {
  /** 调用 GET /api/v1/health */
  check(): Promise<HealthResponse> {
    return apiClient.get<HealthResponse>('/health').then(r => r.data)
  },
}
