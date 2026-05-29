import axios from 'axios'

const BASE_URL = '/api/v1/dashboard'

export interface DashboardOrder {
  order_id: number
  order_no: string
  customer_code?: string
  salesperson?: string
  internal_code: string
  product_cn?: string
  order_quantity?: number
  order_unit_price?: number
  order_total?: number
  pi_quantity?: number
  pi_unit_price?: number
  pi_total?: number
  association_status: 'full' | 'partial' | 'none'
  diff_status: string
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
  const response = await axios.get<DashboardResponse>(`${BASE_URL}/orders`, { params })
  return response.data
}

export const exportDashboardExcel = (params?: {
  search?: string
  status?: string
}) => {
  const queryString = params ? `?${new URLSearchParams(params as any).toString()}` : ''
  window.location.href = `${BASE_URL}/export${queryString}`
}