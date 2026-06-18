import { apiClient } from '@/api/axios'

const BASE_URL = '/api/v1/dashboard'

export interface DashboardProduct {
  id: number
  internal_code: string
  product_cn: string
  product_en: string
  spec_kg: number | null
  quantity_kg: number | null
  unit_price: number | null
  total_amount: number | null
  hs_code: string
  customs_name: string
  drum_count: number | null
  pallet_count: number | null
  gross_weight_kg: number | null
  volume_cbm: number | null
  fits_20gp: string
}

export interface DashboardOrder {
  order_id: number
  order_no: string
  customer_code: string
  salesperson: string
  pi_no: string
  status: string
  created_at: string | null
  products: DashboardProduct[]
  product_count: number
}

export interface DashboardResponse {
  orders: DashboardOrder[]
  total: number
  page: number
  page_size: number
}

export const getDashboardOrders = async (params: {
  search?: string
  status?: string
  page?: number
  page_size?: number
}): Promise<DashboardResponse> => {
  const response = await apiClient.get<DashboardResponse>(`${BASE_URL}/orders`, { params })
  return response.data
}

export const deleteDashboardOrder = async (recordId: number) => {
  await apiClient.delete(`${BASE_URL}/records/${recordId}`)
}

export const exportDashboardExcel = (params?: {
  search?: string
  status?: string
}) => {
  const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : ''
  window.location.href = `${BASE_URL}/export${queryString}`
}