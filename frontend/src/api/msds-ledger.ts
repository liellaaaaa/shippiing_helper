import { apiClient } from '@/api/axios'

export interface MsdsLedgerItem {
  id: number
  internal_code: string
  customs_name: string
  appearance: string
  ion_type: string
  ph: string
  composition: CompositionItem[]
  product_name_en: string
  appearance_en: string
  ion_type_en: string
  version: number
}

export interface CompositionItem {
  component_cn: string
  component_en: string
  cas: string
  percentage: string
}

export interface GenerateMsdsRequest {
  ledger_id: number
  language: 'cn' | 'en'
  msds_number: string
  revision_date: string
}

export interface BatchGenerateMsdsRequest {
  ledger_ids: number[]
  overrides?: Record<string, { msds_number?: string; revision_date?: string }>
  output_format?: 'docx' | 'pdf'
}

export const msdsLedgerApi = {
  list(params?: { keyword?: string; internal_code?: string }) {
    return apiClient.get<{ items: MsdsLedgerItem[] }>('/msds-ledger', { params })
  },

  get(id: number) {
    return apiClient.get<MsdsLedgerItem>(`/msds-ledger/${id}`)
  },

  create(data: Partial<MsdsLedgerItem>) {
    return apiClient.post<MsdsLedgerItem>('/msds-ledger', data)
  },

  update(id: number, data: Partial<MsdsLedgerItem>) {
    return apiClient.put<MsdsLedgerItem>(`/msds-ledger/${id}`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/msds-ledger/${id}`)
  },

  generate(request: GenerateMsdsRequest) {
    return apiClient.post('/msds-ledger/generate', request)
  },

  batchGenerate(request: BatchGenerateMsdsRequest) {
    return apiClient.post('/msds-ledger/batch-generate', request, { responseType: 'blob' })
  },
}
