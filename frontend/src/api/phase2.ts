import { apiClient } from '@/api/axios'

export const phase2Api = {
  generateBooking(fields: {
    shipper: string
    consignee: string
    notify: string
    cut_off_date: string
    place_of_receipt: string
    pol: string
    pod: string
    place_of_delivery: string
    marks: string
    no_kind_pkg: string
    customs_names: string[]
    gross_weight: string
    measurement: string
    template_type?: 'xls' | 'xlsx'
  }) {
    return apiClient.post('/documents/booking', fields)
  },
  generateMsds(product: string) {
    return apiClient.get('/documents/msds', { params: { product } })
  },
  generateCustoms(orderId: number | null, ledgerRecordId?: number, companyCode?: string) {
    return apiClient.get('/documents/customs', {
      params: { order_id: orderId, ledger_record_id: ledgerRecordId, company_code: companyCode }
    })
  },
  /** 解析品质检测报告 .docx → 批次列表（COA 多批填充） */
  parseCoaReport(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/documents/coa/parse-report', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  generateClearance(docType: 'ci' | 'pl' | 'coa' | 'si', payload: {
    ledger_record_id: number
    order_id?: number
    customer_code?: string
    company_code?: string
    transport_mode?: 'FCL' | 'LCL'
    overrides?: Record<string, unknown>
  }) {
    return apiClient.post(`/documents/${docType}`, payload)
  },
  /** 另存为本客户模板（一客一模板） */
  saveCustomerTemplate(payload: {
    customer_code: string
    doc_type: 'ci' | 'pl' | 'coa' | 'si'
    company_code?: string
    template_base64?: string
    options?: Record<string, unknown>
    created_by?: string
  }) {
    return apiClient.post('/documents/templates/save', payload)
  },
  listCustomerTemplates(customerCode?: string) {
    return apiClient.get('/documents/templates', { params: { customer_code: customerCode } })
  },
  getDocHistory(orderId: number) {
    return apiClient.get(`/documents/history/${orderId}`)
  },
  listMsds(params: { page?: number; pageSize?: number; search?: string }) {
    return apiClient.get('/msds', { params })
  },
  getMsdsContent(id: number) {
    return apiClient.get(`/msds/${id}/content`)
  },
  loadMsds(msdsId: number) {
    return apiClient.get(`/documents/msds/${msdsId}`)
  },
  reindexMsds() {
    return apiClient.post('/msds/reindex')
  },
  uploadTransportReport(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/transport/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  getExportCodes(internalCode: string) {
    return apiClient.get('/export-codes', { params: { internal_code: internalCode } })
  },

  // ── 数据中心 ───────────────────────────────────────────────
  searchDataCenter(query: string) {
    return apiClient.get('/data-center/search', { params: { q: query } })
  },
  getDataCenterFileUrl(fileId: number) {
    return `/data-center/files/${fileId}`
  },
  getDataCenterSummary(fileId: number) {
    return apiClient.get(`/data-center/summary/${fileId}`)
  },
  uploadCorrectedMsds(fileId: number, file: File, user: string = 'admin') {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/data-center/upload-corrected/${fileId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { user },
    })
  },
  reindexDataCenter() {
    return apiClient.post('/data-center/reindex')
  },
  getDataCenterTree() {
    return apiClient.get('/data-center/tree')
  },

  // ── 运输鉴定报告 ─────────────────────────────────────────────
  searchTransportReports(query: string) {
    return apiClient.get('/transport-reports/search', { params: { q: query } })
  },
  searchTransportReportsByName(query: string) {
    return apiClient.get('/transport-reports/search-by-name', { params: { q: query } })
  },
  getLinkedReports(orderItemId: number) {
    return apiClient.get(`/transport-reports/linked/${orderItemId}`)
  },
  linkTransportReport(orderItemId: number, transportReportId: number) {
    return apiClient.post('/transport-reports/link', null, {
      params: { order_item_id: orderItemId, transport_report_id: transportReportId },
    })
  },
  unlinkTransportReport(linkId: number) {
    return apiClient.delete(`/transport-reports/unlink/${linkId}`)
  },
  getTransportReportFileUrl(filename: string) {
    return `/transport-reports/files/${encodeURIComponent(filename)}`
  },
  reindexTransportReports() {
    return apiClient.post('/transport-reports/reindex')
  },
}