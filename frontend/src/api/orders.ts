import { apiClient } from '@/api/axios'

export interface OrderItemSchema {
  internal_code: string
  product_cn?: string
  product_en?: string
  spec_kg?: number
  hs_code?: string
  customs_name?: string
  customs_ingredients?: string
  quantity_kg?: number
  unit_price?: number
  total_amount?: number
  packaging_type_id?: number
  pallet_spec?: string
  drums_per_pallet?: number
  drum_count?: number
  pallet_count?: number
  net_weight_kg?: number
  gross_weight_kg?: number
  volume_cbm?: number
  hs_code_warning?: string
  warning?: string
  _selected?: boolean
}

export interface ParsedOrderSchema {
  order_no: string
  customer_code?: string
  salesperson?: string
  items: OrderItemSchema[]
  header_conflict_warning?: string
}

export interface SkippedRowSchema {
  line_index: number
  reason: string
  raw_data: string[]
}

export interface PasteParseResponse {
  orders: ParsedOrderSchema[]
  skipped_rows: SkippedRowSchema[]
  warning?: string
}

export interface OrderSaveResponse {
  order_id: number
  items_count: number
  message: string
}

export const ordersApi = {
  parsePaste: async (rawText: string): Promise<PasteParseResponse> => {
    const resp = await apiClient.post(`/orders/paste`, { raw_text: rawText })
    return resp.data
  },

  saveOrder: async (order: ParsedOrderSchema): Promise<OrderSaveResponse> => {
    const resp = await apiClient.post(`/orders`, { order })
    return resp.data
  }
}