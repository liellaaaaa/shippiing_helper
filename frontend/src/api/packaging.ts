import { apiClient } from '@/api/axios'

export interface PackageType {
  name: string
  dims: string
  cbm: number
  tare_kg: number
  gross_kg: number
  net_kg: number
  barrel_type: string
  is_palletizable: boolean
  no_pallet_qty: number | null
  pallet_qty_1x1: number | null
  pallet_qty_1_1x1_1: number | null
}

export interface PalletType {
  name: string
  dims: string
  weight_kg: number
  cbm: number
}

export interface PackingScheme {
  drums: number
  pallets: number
  drums_per_pallet: number
  pallet_type: string | null
  total_cbm: number
  total_weight_kg: number
  fits_20gp: boolean
  fits_40gp: boolean
  recommended: string
  remainder: number  // 余数桶数
  full_pallets: number  // 整板数
}

export interface CalculateRequest {
  packaging_name: string
  order_qty_kg: number
  use_pallet: boolean
  pallet_name?: string
}

const packagingApi = {
  /** 获取所有包装种类 */
  getTypes(): Promise<PackageType[]> {
    return apiClient.get('/api/v1/packaging/types').then(r => r.data)
  },

  /** 获取所有托盘种类 */
  getPallets(): Promise<PalletType[]> {
    return apiClient.get('/api/v1/packaging/pallets').then(r => r.data)
  },

  /** 计算包装方案 */
  calculate(data: CalculateRequest): Promise<PackingScheme> {
    return apiClient.post('/api/v1/packaging/calculate', data).then(r => r.data)
  },

  /** 计算所有可用方案 */
  calculateSchemes(data: CalculateRequest): Promise<PackingScheme[]> {
    return apiClient.post('/api/v1/packaging/calculate-schemes', data).then(r => r.data)
  },
}

export default packagingApi