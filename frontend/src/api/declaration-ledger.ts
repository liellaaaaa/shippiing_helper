import apiClient from './axios'

export interface HsCodeField {
  field_name: string
  field_type: string
  sort_order: number
  is_required: boolean
}

export interface DeclarationProduct {
  id: number
  hs_code: string
  product_name: string
  website_name: string | null
  product_description: string | null
  values: Record<string, string>
}

export interface HsCodeDetail {
  hs_code: string
  website_name: string | null
  description: string | null
  fields: HsCodeField[]
  products: DeclarationProduct[]
}

export interface HsCodeListItem {
  hs_code: string
  website_name: string | null
  product_count: number
}

export interface ProductCreateData {
  product_name: string
  website_name?: string
  product_description?: string
}

export interface ProductUpdateData {
  product_name?: string
  website_name?: string
  product_description?: string
}

export interface ValuesUpdateData {
  values: Record<string, string>
}

export interface FieldCreateData {
  field_name: string
  field_type?: string
  sort_order?: number
  is_required?: boolean
}

export interface FieldUpdateData {
  field_name?: string
  field_type?: string
  sort_order?: number
  is_required?: boolean
}

export const declarationLedgerApi = {
  // HS Code 列表
  listHsCodes(keyword?: string) {
    return apiClient.get<HsCodeListItem[]>('/declaration-ledger/hs-codes', {
      params: { keyword }
    })
  },

  // HS Code 详情
  getHsCodeDetail(hsCode: string) {
    return apiClient.get<HsCodeDetail>(`/declaration-ledger/hs-codes/${hsCode}`)
  },

  // 新增产品
  createProduct(hsCode: string, data: ProductCreateData) {
    return apiClient.post<DeclarationProduct>(
      `/declaration-ledger/hs-codes/${hsCode}/products`,
      data
    )
  },

  // 更新产品
  updateProduct(productId: number, data: ProductUpdateData) {
    return apiClient.put<DeclarationProduct>(
      `/declaration-ledger/products/${productId}`,
      data
    )
  },

  // 删除产品
  deleteProduct(productId: number) {
    return apiClient.delete(`/declaration-ledger/products/${productId}`)
  },

  // 批量更新要素值
  updateValues(productId: number, data: ValuesUpdateData) {
    return apiClient.put<DeclarationProduct>(
      `/declaration-ledger/products/${productId}/values`,
      data
    )
  },

  // 新增字段
  createField(hsCode: string, data: FieldCreateData) {
    return apiClient.post<HsCodeField>(
      '/declaration-ledger/fields',
      data,
      { params: { hs_code: hsCode } }
    )
  },

  // 更新字段
  updateField(fieldId: number, data: FieldUpdateData) {
    return apiClient.put<HsCodeField>(
      `/declaration-ledger/fields/${fieldId}`,
      data
    )
  },

  // 删除字段
  deleteField(fieldId: number) {
    return apiClient.delete(`/declaration-ledger/fields/${fieldId}`)
  }
}
