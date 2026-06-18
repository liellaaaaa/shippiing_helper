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
    return apiClient.post('/api/v1/documents/booking', fields)
  },
  generateLoi(orderNo: string, piNo: string) {
    return apiClient.get('/api/v1/documents/loi', { params: { order_no: orderNo, pi_no: piNo } })
  },
  generateMsds(product: string) {
    return apiClient.get('/api/v1/documents/msds', { params: { product } })
  },
  generateCustoms(orderId: number | null) {
    return apiClient.get('/api/v1/documents/customs', {
      params: { order_id: orderId }
    })
  },
  getDocHistory(orderId: number) {
    return apiClient.get(`/api/v1/documents/history/${orderId}`)
  },
  listMsds(params: { page?: number; pageSize?: number; search?: string }) {
    return apiClient.get('/api/v1/msds', { params })
  },
  getMsdsContent(id: number) {
    return apiClient.get(`/api/v1/msds/${id}/content`)
  },
  loadMsds(msdsId: number) {
    return apiClient.get(`/api/v1/documents/msds/${msdsId}`)
  },
  reindexMsds() {
    return apiClient.post('/api/v1/msds/reindex')
  },
  uploadTransportReport(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/api/v1/transport/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  getExportCodes(internalCode: string) {
    return apiClient.get('/api/v1/export-codes', { params: { internal_code: internalCode } })
  },
  getJwt(documentKey: string, fileType: string) {
    return apiClient.post('/api/v1/onlyoffice/jwt', null, { params: { documentKey, fileType } })
  },
  openBlankTemplate(type: 'booking' | 'loi' | 'msds') {
    return apiClient.get(`/api/v1/documents/template/${type}`)
  },
  listMyTemplates() {
    return apiClient.get('/api/v1/documents/my-templates')
  },

  // ── 数据中心 ───────────────────────────────────────────────
  searchDataCenter(query: string) {
    return apiClient.get('/api/v1/data-center/search', { params: { q: query } })
  },
  getDataCenterFileUrl(fileId: number) {
    return `/api/v1/data-center/files/${fileId}`
  },
  getDataCenterSummary(fileId: number) {
    return apiClient.get(`/api/v1/data-center/summary/${fileId}`)
  },
  uploadCorrectedMsds(fileId: number, file: File, user: string = 'admin') {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/api/v1/data-center/upload-corrected/${fileId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { user },
    })
  },
  reindexDataCenter() {
    return apiClient.post('/api/v1/data-center/reindex')
  },
  getDataCenterTree() {
    return apiClient.get('/api/v1/data-center/tree')
  },

  // ── 运输鉴定报告 ─────────────────────────────────────────────
  searchTransportReports(query: string) {
    return apiClient.get('/api/v1/transport-reports/search', { params: { q: query } })
  },
  getTransportReportFileUrl(filename: string) {
    return `/api/v1/transport-reports/files/${encodeURIComponent(filename)}`
  },
  reindexTransportReports() {
    return apiClient.post('/api/v1/transport-reports/reindex')
  },
}