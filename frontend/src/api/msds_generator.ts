import { apiClient } from '@/api/axios'

export interface MSDSFile {
  name: string
  path: string
}

export interface CompositionItem {
  component_cn: string
  cas: string
  percentage: string
}

export interface Physicochemical {
  physical_form?: string
  ion_type?: string
  ph?: string
  [key: string]: string | undefined
}

export interface PhysicochemicalEdit {
  appearance?: string
  ion_type?: string
  ph?: string
  melting_point?: string
  boiling_point?: string
  density?: string
  flash_point?: string
  solubility?: string
}

export interface GenerateRequest {
  msds_file_path: string
  product_name?: string
  composition: CompositionItem[]
  physicochemical?: PhysicochemicalEdit
}

export interface MSDSParseResult {
  product_name: string
  composition: CompositionItem[]
  physicochemical: Physicochemical
}

export const msdsGeneratorApi = {
  /**
   * 搜索旧 MSDS 文件
   */
  searchMSDS(keyword: string): Promise<{ files: MSDSFile[] }> {
    return apiClient.get('/msds-generator/search', { params: { keyword } })
  },

  /**
   * 解析旧 MSDS 文件，提取产品信息、成分、理化特性
   */
  parseMSDS(filePath: string): Promise<MSDSParseResult> {
    return apiClient.post('/msds-generator/parse', { filePath })
  },

  /**
   * 生成 MSDS 文档
   */
  generate(request: GenerateRequest) {
    return apiClient.post('/msds-generator/generate', request)
  },
}
