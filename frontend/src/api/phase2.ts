import axios from 'axios'

export const phase2Api = {
  generateBooking(orderId: number, templateType: 'xls' | 'xlsx' = 'xls') {
    return axios.get('/api/v1/documents/booking', { params: { order_id: orderId, template_type: templateType } })
  },
  generateLoi(orderNo: string, piNo: string) {
    return axios.get('/api/v1/documents/loi', { params: { order_no: orderNo, pi_no: piNo } })
  },
  generateMsds(product: string) {
    return axios.get('/api/v1/documents/msds', { params: { product } })
  },
  generateCustoms(orderId: number | null) {
    return axios.get('/api/v1/documents/customs', {
      params: { order_id: orderId }
    })
  },
  getDocHistory(orderId: number) {
    return axios.get(`/api/v1/documents/history/${orderId}`)
  },
  listMsds(params: { page?: number; pageSize?: number; search?: string }) {
    return axios.get('/api/v1/msds', { params })
  },
  getMsdsContent(id: number) {
    return axios.get(`/api/v1/msds/${id}/content`)
  },
  loadMsds(msdsId: number) {
    return axios.get(`/api/v1/documents/msds/${msdsId}`)
  },
  reindexMsds() {
    return axios.post('/api/v1/msds/reindex')
  },
  uploadTransportReport(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return axios.post('/api/v1/transport/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  getExportCodes(internalCode: string) {
    return axios.get('/api/v1/export-codes', { params: { internal_code: internalCode } })
  },
  getJwt(documentKey: string, fileType: string) {
    return axios.post('/api/v1/onlyoffice/jwt', null, { params: { documentKey, fileType } })
  },
  openBlankTemplate(type: 'booking' | 'loi' | 'msds') {
    return axios.get(`/api/v1/documents/template/${type}`)
  },
  listMyTemplates() {
    return axios.get('/api/v1/documents/my-templates')
  },

  // ── 数据中心 ───────────────────────────────────────────────
  searchDataCenter(query: string) {
    return axios.get('/api/v1/data-center/search', { params: { q: query } })
  },
  getDataCenterFileUrl(fileId: number) {
    return `/api/v1/data-center/files/${fileId}`
  },
  getDataCenterSummary(fileId: number) {
    return axios.get(`/api/v1/data-center/summary/${fileId}`)
  },
  uploadCorrectedMsds(fileId: number, file: File, user: string = 'admin') {
    const formData = new FormData()
    formData.append('file', file)
    return axios.post(`/api/v1/data-center/upload-corrected/${fileId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { user },
    })
  },
  reindexDataCenter() {
    return axios.post('/api/v1/data-center/reindex')
  },

  // ── 运输鉴定报告 ─────────────────────────────────────────────
  searchTransportReports(query: string) {
    return axios.get('/api/v1/transport-reports/search', { params: { q: query } })
  },
  getTransportReportFileUrl(filename: string) {
    return `/api/v1/transport-reports/files/${encodeURIComponent(filename)}`
  },
  reindexTransportReports() {
    return axios.post('/api/v1/transport-reports/reindex')
  },
}