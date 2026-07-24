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
  generateCustoms(orderId: number | null, ledgerRecordId?: number) {
    return apiClient.get('/documents/customs', {
      params: { order_id: orderId, ledger_record_id: ledgerRecordId }
    })
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
  getJwt(documentKey: string, fileType: string) {
    return apiClient.post('/onlyoffice/jwt', null, { params: { documentKey, fileType } })
  },
  openBlankTemplate(type: 'booking' | 'msds') {
    return apiClient.get(`/documents/template/${type}`)
  },
  listMyTemplates() {
    return apiClient.get('/documents/my-templates')
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