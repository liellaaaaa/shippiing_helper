import axios from 'axios'

const BASE_URL = '/api/v1/pi'

export interface PiContractItem {
  row_index: number
  status: 'success' | 'error'
  error_msg?: string
  internal_code?: string
  quantity?: number
  unit_price?: number
  total_amount?: number
  product_color?: string
  hs_code?: string
  customs_name?: string
  customs_composition?: string
  order_customs_name?: string
  notes?: string
  _missing_fields: string[]
}

export interface Confidence {
  recognized: number
  total: number
  percentage: string
  failed_rows: number
}

export interface PiUploadResponse {
  pi_no: string
  customer_code?: string
  sales_person?: string
  pi_date?: string
  is_ordered: string
  // PI Header 字段（后端 PiContractUploadResponse 已支持）
  consignee_name?: string
  consignee_address?: string
  destination?: string
  loading_port?: string
  price_term?: string
  invoice_to?: string
  items: PiContractItem[]
  confidence: Confidence
}

export interface PiSaveItem {
  internal_code: string
  quantity?: number
  unit_price?: number
  total_amount?: number
  product_color?: string
  hs_code?: string
  customs_name?: string
  customs_composition?: string
  order_customs_name?: string
  notes?: string
}

export interface PiSaveRequest {
  pi_no: string
  customer_code?: string
  sales_person?: string
  pi_date?: string
  is_ordered: string
  order_id?: number
  items: PiSaveItem[]
}

export interface PiSaveResponse {
  contract_id: number
  items_count: number
  pi_data_updated: number
  message: string
}

export interface PiQueryResponse {
  contracts: Array<{
    id: number
    pi_no: string
    customer_code?: string
    sales_person?: string
    pi_date?: string
    is_ordered: string
    items: PiContractItem[]
  }>
}

export const uploadPiFile = async (file: File): Promise<PiUploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  // Do NOT set Content-Type header manually — axios must set it with boundary
  const response = await axios.post<PiUploadResponse>(`${BASE_URL}/upload`, formData)
  return response.data
}

export const savePiContract = async (data: PiSaveRequest): Promise<PiSaveResponse> => {
  const response = await axios.post<PiSaveResponse>(`${BASE_URL}/contracts`, data)
  return response.data
}

export const queryPiContracts = async (params: {
  pi_no?: string
  customer_code?: string
  internal_code?: string
}): Promise<PiQueryResponse> => {
  const response = await axios.get<PiQueryResponse>(`${BASE_URL}/contracts`, { params })
  return response.data
}