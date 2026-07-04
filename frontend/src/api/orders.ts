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

// ── 台账相关类型 ─────────────────────────────────────────────────────────────

export interface LedgerItem {
  internal_code: string
  product_cn?: string
  product_en?: string
  spec_kg?: number
  quantity_kg?: number
  unit_price?: number
  total_amount?: number
  hs_code?: string
  customs_name?: string
  customs_ingredients?: string
  product_appearance?: string
  packaging_type_id?: number
  pallet_spec?: string
  drums_per_pallet?: number
  drum_count?: number
  pallet_count?: number
  net_weight_kg?: number
  gross_weight_kg?: number
  volume_cbm?: number
  fits_20gp?: string
}

export interface ValidationWarning {
  internal_code: string
  field: string
  pi_contract_value?: string | number
  pi_file_value?: string | number
  sales_order_value?: string | number
  message: string
}

export interface MergePreviewItem {
  internal_code: string
  source_pi_contract: boolean
  source_sales_order: boolean
  source_pi_file: boolean
  product_cn?: string
  quantity_kg?: number
  unit_price?: number
  total_amount?: number
  hs_code?: string
  customs_name?: string
  customs_ingredients?: string
  product_appearance?: string
  validation_status: string
  warnings: ValidationWarning[]
}

export interface MergePreviewResponse {
  order_no: string
  customer_code?: string
  sales_person?: string
  pi_date?: string
  shipment_title?: string
  merchandiser?: string
  delivery_date?: string
  shipment_method?: string
  consignee_name?: string
  consignee_address?: string
  consignee_tel?: string
  destination?: string
  loading_port?: string
  price_term?: string
  payment_terms?: string
  bank_info?: string
  items: MergePreviewItem[]
  validation_status: string
  validation_warnings: ValidationWarning[]
  pi_contract_table_parsed?: any
  sales_order_table_parsed?: any
  pi_file_parsed?: any
}

export interface LedgerRecord {
  id: number
  order_no: string
  customer_code?: string
  sales_person?: string
  pi_no?: string
  pi_date?: string
  sales_order_no?: string
  merchandiser?: string
  order_date?: string
  delivery_date?: string
  shipment_channel?: string
  shipment_method?: string
  review_status?: string
  spec_abnormal?: string
  has_sample?: string
  price_adjusted?: string
  order_confirmed?: string
  production_deadline?: string
  shipment_title?: string
  document_type?: string
  consignee_name?: string
  consignee_address?: string
  consignee_tel?: string
  destination?: string
  loading_port?: string
  price_term?: string
  payment_terms?: string
  bank_info?: string
  items: LedgerItem[]
  status: string
  created_at?: string
}

export interface LedgerWriteRequest {
  order_no: string
  customer_code?: string
  sales_person?: string
  pi_date?: string
  sales_order_no?: string
  merchandiser?: string
  order_date?: string
  delivery_date?: string
  shipment_channel?: string
  shipment_method?: string
  review_status?: string
  spec_abnormal?: string
  has_sample?: string
  price_adjusted?: string
  order_confirmed?: string
  production_deadline?: string
  shipment_title?: string
  document_type?: string
  consignee_name?: string
  consignee_address?: string
  consignee_tel?: string
  destination?: string
  loading_port?: string
  price_term?: string
  payment_terms?: string
  bank_info?: string
  items: LedgerItem[]
}

export interface LedgerWriteResponse {
  record_id: number
  items_count: number
  message: string
}

export const ordersApi = {
  parsePaste: async (rawText: string): Promise<PasteParseResponse> => {
    const resp = await apiClient.post(`/orders/paste`, { raw_text: rawText })
    return resp.data
  },

  // ── 台账模式 API ───────────────────────────────────────────────────────────

  /** 解析 PI 合同表粘贴文本 */
  parsePiContractTable: async (rawText: string): Promise<PasteParseResponse> => {
    const resp = await apiClient.post(`/orders/pi-contract-paste`, { raw_text: rawText })
    return resp.data
  },

  /** 解析销售订单表粘贴文本 */
  parseSalesOrderTable: async (rawText: string): Promise<PasteParseResponse> => {
    const resp = await apiClient.post(`/orders/sales-order-paste`, { raw_text: rawText })
    return resp.data
  },

  /** 三源合并预览 */
  mergePreview: async (formData: FormData): Promise<MergePreviewResponse> => {
    const resp = await apiClient.post(`/orders/merge-preview`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return resp.data
  },

  /** 写入台账 */
  writeLedger: async (data: LedgerWriteRequest): Promise<LedgerWriteResponse> => {
    const resp = await apiClient.post(`/orders/ledger`, data)
    return resp.data
  },

  /** 读取单条台账记录 */
  getLedgerRecord: async (recordId: number): Promise<LedgerRecord> => {
    const resp = await apiClient.get(`/orders/ledger/${recordId}`)
    return resp.data
  },

  /** 台账列表 */
  listLedger: async (params?: { search?: string; page?: number; page_size?: number }) => {
    const resp = await apiClient.get(`/orders/ledger`, { params })
    return resp.data
  },

  saveOrder: async (order: ParsedOrderSchema): Promise<OrderSaveResponse> => {
    const resp = await apiClient.post(`/orders`, { order })
    return resp.data
  }
}