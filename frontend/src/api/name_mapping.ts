import { apiClient } from '@/api/axios'

export interface NameMapping {
  en: string
  cn: string
}

export const nameMappingApi = {
  getAll: () => apiClient.get<{ mappings: NameMapping[] }>('/name-mapping'),

  lookupByCn: (cn: string) =>
    apiClient.get<{ cn: string; en: string | null }>('/name-mapping/lookup', { params: { cn } }),

  lookupByEn: (en: string) =>
    apiClient.get<{ en: string; cn: string | null }>('/name-mapping/lookup', { params: { en } }),
}