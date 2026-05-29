<template>
  <div class="pi-extract-page">
    <div class="page-header">
      <h1 class="page-title">PI 文件提取</h1>
      <p class="page-subtitle">上传 PI 合同文件，自动解析并关联产品知识库</p>
    </div>

    <div class="page-content">
      <div class="content-left">
        <el-card class="upload-card">
          <template #header>
            <div class="card-header">
              <span>上传 PI 文件</span>
            </div>
          </template>
          <div class="upload-placeholder">
            <PiUploadDragger @fileSelected="handleFileSelected" />
            <el-button size="small" @click="downloadTemplate" style="margin-top: 12px;">下载标准模板</el-button>
          </div>
        </el-card>

        <el-card class="history-card" style="margin-top: 16px;">
          <template #header>
            <div class="card-header">
              <span>历史查询</span>
            </div>
          </template>
          <el-input v-model="searchPiNo" placeholder="搜索 PI 号" />
          <el-button type="primary" style="margin-top: 12px; width: 100%;" @click="queryContracts">
            查询
          </el-button>
        </el-card>
      </div>

      <div class="content-right">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>解析预览</span>
              <el-tag v-if="parsedData" type="success">已解析</el-tag>
            </div>
          </template>
          <div v-if="!parsedData" class="preview-placeholder">
            <p>上传文件后将显示解析结果</p>
          </div>
          <div v-else>
            <PiPreviewTable v-if="parsedData" :data="parsedData!" @saved="handleSaved" />
          </div>
        </el-card>
      </div>
    </div>

    <ColumnMappingModal
      v-if="showMappingModal"
      :confidence-percent="confidencePercent"
      :original-columns="originalColumns"
      @apply="handleMappingApply"
      @save-template="handleMappingSaveTemplate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import PiUploadDragger from '@/components/phase1/PiUploadDragger.vue'
import PiPreviewTable from '@/components/phase1/PiPreviewTable.vue'
import ColumnMappingModal from '@/components/phase1/ColumnMappingModal.vue'
import { uploadPiFile, type PiUploadResponse } from '@/api/pi'

const LOW_CONFIDENCE_THRESHOLD = 60

const searchPiNo = ref('')
const parsedData = ref<PiUploadResponse | null>(null)
const loading = ref(false)
const showMappingModal = ref(false)
const confidencePercent = ref('0%')
const originalColumns = ref<string[]>([])

// Load customer mapping from localStorage
const loadCustomerMapping = (customerCode: string): Record<string, string> | null => {
  try {
    const raw = localStorage.getItem(`pi_mapping_${customerCode}`)
    return raw ? JSON.parse(raw).column_mapping : null
  } catch {
    return null
  }
}

// Save customer mapping to localStorage
const saveCustomerMapping = (customerCode: string, mapping: Record<string, string>) => {
  localStorage.setItem(`pi_mapping_${customerCode}`, JSON.stringify({
    customer_code: customerCode,
    column_mapping: mapping,
    created_at: new Date().toISOString(),
  }))
}

// Download standard PI template
const downloadTemplate = () => {
  const headers = [
    '客户编码', 'PI号', '业务员', '日期', '销售订单号',
    '内部编码', '数量', '单价', '金额', '产品颜色',
    '海关编码', '报关品名', '报关成分', '填写订单报关品名', '是否下单', '备注'
  ]
  const tsv = headers.join('\t') + '\n'
  const blob = new Blob([tsv], { type: 'text/tsv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'PI标准模板.tsv'
  a.click()
  URL.revokeObjectURL(url)
}

const handleFileSelected = async (file: File) => {
  loading.value = true
  try {
    const response = await uploadPiFile(file)
    parsedData.value = response

    const pct = parseInt(response.confidence.percentage)
    confidencePercent.value = `${pct}%`

    if (pct < LOW_CONFIDENCE_THRESHOLD) {
      showMappingModal.value = true
    }

    ElMessage.success('PI 文件解析完成')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '解析失败，请检查文件格式')
    parsedData.value = null
  } finally {
    loading.value = false
  }
}

const queryContracts = () => {
  ElMessage.info('查询功能待实现')
}

// Handle column mapping application
const handleMappingApply = (mapping: Record<string, string>) => {
  ElMessage.info('列映射已应用（重新解析功能待实现）')
}

// Handle save as customer template
const handleMappingSaveTemplate = (mapping: Record<string, string>) => {
  const customerCode = parsedData.value?.customer_code || 'unknown'
  saveCustomerMapping(customerCode, mapping)
}

// Handle PI saved success
const handleSaved = () => {
  ElMessage.success('PI 合同保存成功')
}
</script>

<style scoped>
.pi-extract-page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 28px; font-weight: 600; color: var(--color-text-primary, #303133); margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: var(--color-text-secondary, #909399); margin: 0; }

.page-content { display: grid; grid-template-columns: 400px 1fr; gap: 20px; }
.content-left { display: flex; flex-direction: column; }
.content-right { min-height: 400px; }

.upload-card, .history-card { border-radius: 12px; }
.card-header { font-weight: 600; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }

.upload-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 20px; color: var(--color-text-secondary, #909399); }
.upload-placeholder .el-icon { color: var(--color-primary, #0077cc); margin-bottom: 16px; }
.upload-placeholder p { margin: 4px 0; }
.upload-hint { font-size: 12px; color: var(--color-text-placeholder, #c0c4cc); }

.preview-placeholder { display: flex; align-items: center; justify-content: center; height: 200px; color: var(--color-text-placeholder, #c0c4cc); }
</style>