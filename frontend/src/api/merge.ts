import { apiClient } from '@/api/axios'

export interface OrderListItem {
  id: number
  order_no: string
  customer_code?: string
  salesperson?: string
  total_amount?: number
  association_status: 'full' | 'partial' | 'none'
  items_count: number
  linked_count: number
  pi_no?: string
  created_at?: string
}

export interface OrderListResponse {
  orders: OrderListItem[]
  total: number
  page: number
  page_size: number
}

export interface OrderItemData {
  quantity?: number
  unit_price?: number
  total_amount?: number
  hs_code?: string
  customs_name?: string
}

export interface DiffInfo {
  status: string  // "一致" | "数量不符" | "单价不符" | "金额不符" | "HS不符" | "PI未覆盖"
  flags: string[]
  order_value?: number
  pi_value?: number
}

export interface ComparisonItem {
  internal_code: string
  product_cn?: string
  order?: OrderItemData
  pi?: OrderItemData
  diff: DiffInfo
}

export interface OrderComparisonResponse {
  order_id: number
  order_no: string
  customer_code?: string
  pi_no?: string
  drum_count?: number
  pallet_count?: number
  gross_weight_kg?: number
  volume_cbm?: number
  fits_20gp?: string
  items: ComparisonItem[]
}

export const getOrderList = async (params: {
  tab?: string
  search?: string
  page?: number
  page_size?: number
}): Promise<OrderListResponse> => {
  const response = await apiClient.get<OrderListResponse>(`/merge/orders`, { params })
  return response.data
}

export const getOrderComparison = async (orderId: number): Promise<OrderComparisonResponse> => {
  const response = await apiClient.get<OrderComparisonResponse>(`/merge/orders/${orderId}/comparison`)
  return response.data
}

export const getOrderPiContracts = async (orderId: number): Promise<{pi_no: string; consignee_name: string; consignee_address: string; destination: string}[]> => {
  const response = await apiClient.get<{pi_no: string; consignee_name: string; consignee_address: string; destination: string}[]>(`/merge/orders/${orderId}/pi-contracts`)
  return response.data
}