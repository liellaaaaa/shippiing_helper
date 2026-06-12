import axios from 'axios'

export interface NameMapping {
  en: string
  cn: string
}

export const nameMappingApi = {
  getAll: () => axios.get<{ mappings: NameMapping[] }>('/api/v1/name-mapping'),

  lookupByCn: (cn: string) =>
    axios.get<{ cn: string; en: string | null }>('/api/v1/name-mapping/lookup', { params: { cn } }),

  lookupByEn: (en: string) =>
    axios.get<{ en: string; cn: string | null }>('/api/v1/name-mapping/lookup', { params: { en } }),
}