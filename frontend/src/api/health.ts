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
  /** 调用 GET /health（无需认证，走 nginx 代理到后端） */
  check(): Promise<HealthResponse> {
    return fetch('/health').then(r => r.json())
  },
}
