import { apiClient } from '@/api/axios'

const BASE_URL = '/api/v1/dashboard'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface PackagingResult {
  packaging_type: string
  pallet_spec?: string
  drums: number
  pallets: number
  drums_per_pallet: number
  net_weight_kg: number
  gross_weight_kg: number
  volume_cbm: number
  fits_20gp: string
  load_rate?: number
  packing_scheme?: string
  no_pallet: boolean
}

export interface OrderDataItem {
  internal_code: string
  product_cn?: string
  product_en?: string
  spec_kg?: number
  quantity_kg?: number
  unit_price?: number
  total_amount?: number
  hs_code?: string
  customs_name?: string
  order_requirement?: string
  notes?: string
}

export interface OrderData {
  order_no: string
  customer_code?: string
  customer_name?: string
  sales_person?: string
  order_date?: string
  delivery_date?: string
  items: OrderDataItem[]  // 多产品支持
}

export interface PiData {
  pi_no: string
  customer_code?: string
  pi_date?: string
  internal_code: string
  quantity?: number
  unit_price?: number
  total_amount?: number
  hs_code?: string
  customs_name?: string
}

export interface SaveRecordRequest {
  order_data: OrderData
  pi_data?: PiData
  packaging_result?: PackagingResult
  packaging_items?: any[]
}

export interface SaveRecordResponse {
  record_id: number
  status: string
  message: string
}

export interface OrderPiRecord {
  id: number
  order_no?: string
  customer_code?: string
  customer_name?: string
  pi_no?: string
  sales_person?: string
  order_date?: string
  pi_date?: string
  delivery_date?: string
  internal_code?: string
  product_cn?: string
  product_en?: string
  spec_kg?: number
  hs_code?: string
  customs_name?: string
  quantity_kg?: number
  unit_price?: number
  total_amount?: number
  order_requirement?: string
  notes?: string
  packaging_type_id?: number
  pallet_spec?: string
  drums_per_pallet?: number
  drum_count?: number
  pallet_count?: number
  net_weight_kg?: number
  gross_weight_kg?: number
  volume_cbm?: number
  fits_20gp?: string
  packaging_result_json?: string
  status: string
  created_at?: string
  updated_at?: string
}

// ─── API ──────────────────────────────────────────────────────────────────────

export const saveOrderPiRecord = async (data: SaveRecordRequest): Promise<SaveRecordResponse> => {
  const resp = await apiClient.post<SaveRecordResponse>(`${BASE_URL}/records`, data)
  return resp.data
}

export const queryOrderPiRecords = async (params?: {
  status?: string
  search?: string
  page?: number
  page_size?: number
}) => {
  const resp = await apiClient.get(`${BASE_URL}/records`, { params })
  return resp.data
}

export const getOrderPiRecord = async (id: number): Promise<OrderPiRecord> => {
  const resp = await apiClient.get(`${BASE_URL}/records/${id}`)
  return resp.data
}