import axios from 'axios'

const BASE_URL = '/api/v1'

export const phase2Api = {
  generateBooking(orderId: number) {
    return axios.get('/documents/booking', { params: { order_id: orderId } })
  },
  generateLoi(orderId: number, piNo: string) {
    return axios.get('/documents/loi', { params: { order_id: orderId, pi_no: piNo } })
  },
  generateMsds(product: string) {
    return axios.get('/documents/msds', { params: { product } })
  },
  getDocHistory(orderId: number) {
    return axios.get(`/documents/history/${orderId}`)
  },
  listMsds(params: { page?: number; pageSize?: number; search?: string }) {
    return axios.get('/msds', { params })
  },
  getMsdsContent(id: number) {
    return axios.get(`/msds/${id}/content`)
  },
  reindexMsds() {
    return axios.post('/msds/reindex')
  },
  uploadTransportReport(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return axios.post('/transport/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  getExportCodes(internalCode: string) {
    return axios.get('/export-codes', { params: { internal_code: internalCode } })
  },
  getJwt(documentKey: string, fileType: string) {
    return axios.post('/onlyoffice/jwt', null, { params: { documentKey, fileType } })
  },
}