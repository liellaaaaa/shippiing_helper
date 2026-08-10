import { apiClient } from '@/api/axios'

export interface DeclarationElement {
  id: number
  hs_code: string
  declaration_name: string
  elements_text: string
}

export interface ElementCreateData {
  hs_code: string
  declaration_name: string
  elements_text: string
}

export interface ElementUpdateData {
  hs_code?: string
  declaration_name?: string
  elements_text?: string
}

export const declarationElementsApi = {
  list(params?: { keyword?: string; page?: number; size?: number }) {
    return apiClient.get<{ items: DeclarationElement[]; total: number; page: number; size: number }>(
      '/declaration-elements',
      { params }
    )
  },

  get(id: number) {
    return apiClient.get<DeclarationElement>(`/declaration-elements/${id}`)
  },

  create(data: ElementCreateData) {
    return apiClient.post<DeclarationElement>('/declaration-elements', data)
  },

  update(id: number, data: ElementUpdateData) {
    return apiClient.put<DeclarationElement>(`/declaration-elements/${id}`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/declaration-elements/${id}`)
  },
}
