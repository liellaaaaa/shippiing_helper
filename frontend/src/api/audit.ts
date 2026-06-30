import { apiClient } from '@/api/axios'

export interface AuditLog {
  id: number
  event_type: string
  user_name: string
  module: string | null
  action_time: string
  detail: string | null
  ip_address: string | null
  created_at: string
}

export interface AuditLogsResponse {
  logs: AuditLog[]
  total: number
  page: number
  page_size: number
}

export interface AuditStats {
  by_user: { user_name: string; count: number }[]
  by_event: { event_type: string; count: number }[]
  by_module: { module: string; count: number }[]
}

export const auditApi = {
  getLogs: async (params?: {
    user_name?: string
    event_type?: string
    module?: string
    start_time?: string
    end_time?: string
    page?: number
    page_size?: number
  }): Promise<AuditLogsResponse> => {
    const response = await apiClient.get<AuditLogsResponse>('/audit/logs', { params })
    return response.data
  },

  getStats: async (params?: {
    start_time?: string
    end_time?: string
  }): Promise<AuditStats> => {
    const response = await apiClient.get<AuditStats>('/audit/stats', { params })
    return response.data
  },

  exportExcel: (params?: {
    start_time?: string
    end_time?: string
  }) => {
    const queryString = params
      ? '?' + new URLSearchParams(params as any).toString()
      : ''
    window.location.href = `/api/v1/audit/export${queryString}`
  },
}
