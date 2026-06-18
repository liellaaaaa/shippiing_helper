import { apiClient } from '@/api/axios'

const BASE_URL = '/api/v1/packages'

// ── Types ────────────────────────────────────────────────────────────────────────

export interface PackagingType {
  id: number
  name: string
  net_kg: number
  cbm: number
  pallet_1x1: number | null
  pallet_1_1x1_1: number | null
}

export interface ContainerResult {
  recommended: string
  load_rate: number
  volume_limit: number
  weight_limit: number
  status: string
}

export interface SeaCalculationResult {
  drums: number
  pallets: number
  total_cbm: number
  total_weight_kg: number
  packing_scheme: string
  container: ContainerResult
  packaging: {
    name: string
    drum_cbm: number
    drum_tare_kg: number
    drum_gross_kg: number
    pallet_spec: string
    pallet_capacity: number
  }
}

export interface AirCalculationResult {
  actual_weight_kg: number
  vol_weight_167: number
  vol_weight_6000: number
  chargeable_weight_kg: number
  chargeable_weight_note: string
}

export interface LandCalculationResult {
  total_drums: number
  total_weight_kg: number
  total_cbm: number
  overweight_warning: boolean
}

export type CalculationResult = SeaCalculationResult | AirCalculationResult | LandCalculationResult

export interface RecommendResponse {
  internal_code: string
  recommended_packaging: string | null
  reason: string | null
}

// ── API Functions ─────────────────────────────────────────────────────────────

export const getPackagingTypes = async (): Promise<{ types: PackagingType[] }> => {
  const response = await apiClient.get<{ types: PackagingType[] }>(`${BASE_URL}/types`)
  return response.data
}

export const calculatePackage = async (params: {
  mode?: 'order' | 'manual'
  quantity_kg: number
  packaging_name: string
  pallet_spec?: '1.0x1.0' | '1.1x1.1'
  pallet_qty?: number
  no_pallet?: boolean
  transport_mode?: 'sea' | 'air' | 'land'
  order_id?: number
  internal_code?: string
}): Promise<CalculationResult> => {
  const response = await apiClient.get<CalculationResult>(`${BASE_URL}/calculate`, { params })
  return response.data
}

export const recommendPackaging = async (internalCode: string): Promise<RecommendResponse> => {
  const response = await apiClient.get<RecommendResponse>(`${BASE_URL}/recommend`, {
    params: { internal_code: internalCode }
  })
  return response.data
}