<template>
  <el-dialog
    v-model="visible"
    title="上传品质检测报告"
    width="980px"
    :append-to-body="true"
    class="coa-report-dialog"
    @closed="onClosed"
  >
    <el-upload
      class="coa-uploader"
      drag
      multiple
      accept=".docx"
      :auto-upload="false"
      :show-file-list="false"
      :on-change="handleFileChange"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">
        拖拽检测报告 .docx 到此处，或 <em>点击上传</em>（可多文件，批次自动合并）
      </div>
      <template #tip>
        <div class="el-upload__tip">仅支持 .docx；解析结果可在下表核对后生成 COA</div>
      </template>
    </el-upload>

    <div v-if="parsing" class="parsing-hint">解析中…</div>
    <div v-else-if="rows.length" class="batch-table-wrap">
      <div class="batch-table-title">解析批次（可编辑）· 共 {{ rows.length }} 批</div>
      <el-table :data="rows" border size="small" class="batch-table">
        <el-table-column label="批号" prop="batch_no" min-width="130">
          <template #default="{ row }">
            <el-input v-model="row.batch_no" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="数量" prop="quantity_text" min-width="90">
          <template #default="{ row }">
            <el-input v-model="row.quantity_text" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="pH 标签" prop="ph_label" min-width="120">
          <template #default="{ row }">
            <el-input v-model="row.ph_label" size="small" placeholder="PH (1%) / PH VALUE (20%)" />
          </template>
        </el-table-column>
        <el-table-column label="pH 规格" prop="ph_spec" min-width="90">
          <template #default="{ row }">
            <el-input v-model="row.ph_spec" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="pH 结果" prop="ph_result" min-width="90">
          <template #default="{ row }">
            <el-input v-model="row.ph_result" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="含固量规格" prop="solid_spec" min-width="100">
          <template #default="{ row }">
            <el-input v-model="row.solid_spec" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="含固量结果" prop="solid_result" min-width="100">
          <template #default="{ row }">
            <el-input v-model="row.solid_result" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="外观规格" prop="appearance_spec" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.appearance_spec" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="外观结果" prop="appearance_result" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.appearance_result" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="" width="56" fixed="right">
          <template #default="{ $index }">
            <el-button link type="danger" size="small" @click="rows.splice($index, 1)">删</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div v-else class="empty-hint">上传检测报告后显示解析批次</div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onConfirm">生成 COA</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { phase2Api } from '@/api/phase2'

/** 解析/编辑后的批次行（扁平字段供表格编辑；tests 供后端提取 odour 等） */
export interface CoaBatchRow {
  batch_no: string
  quantity_text: string
  ph_label: string
  ph_spec: string
  ph_result: string
  solid_label: string
  solid_spec: string
  solid_result: string
  appearance_spec: string
  appearance_result: string
  odour_label?: string
  odour_spec?: string
  odour_result?: string
  customer?: string
  product_name_cn?: string
  product_code?: string
  tests?: Array<{
    key: string
    name_cn?: string
    label_en?: string
    spec?: string
    result?: string
  }>
}

const props = defineProps<{ modelValue: boolean }>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'confirm': [batches: CoaBatchRow[]]
}>()

const visible = ref(props.modelValue)
const loading = ref(false)
const parsing = ref(false)
const rows = ref<CoaBatchRow[]>([])

watch(
  () => props.modelValue,
  (v) => {
    visible.value = v
  }
)
watch(visible, (v) => {
  if (v !== props.modelValue) emit('update:modelValue', v)
})

function onClosed() {
  rows.value = []
  parsing.value = false
  loading.value = false
}

function testsToRow(batch: any): CoaBatchRow {
  const tests: any[] = Array.isArray(batch.tests) ? batch.tests : []
  const byKey = (key: string) => tests.find((t: any) => (t?.key || '').toLowerCase() === key)
  const appearance = byKey('appearance')
  const ph = byKey('ph')
  const solid = byKey('solid')
  const odour = byKey('odour')
  return {
    batch_no: batch.batch_no || '',
    quantity_text: batch.quantity_text || '',
    ph_label: ph?.label_en || batch.ph_label || '',
    ph_spec: ph?.spec || batch.ph_spec || '',
    ph_result: ph?.result || batch.ph_result || '',
    solid_label: solid?.label_en || batch.solid_label || 'SOLID CONTENT(%)',
    solid_spec: solid?.spec || batch.solid_spec || '',
    solid_result: solid?.result || batch.solid_result || '',
    appearance_spec: appearance?.spec || batch.appearance_spec || '',
    appearance_result: appearance?.result || batch.appearance_result || '',
    odour_label: odour?.label_en || batch.odour_label || '',
    odour_spec: odour?.spec || batch.odour_spec || '',
    odour_result: odour?.result || batch.odour_result || '',
    customer: batch.customer || '',
    product_name_cn: batch.product_name_cn || '',
    product_code: batch.product_code || '',
    tests,
  }
}

async function handleFileChange(uploadFile: { raw?: File }) {
  const file = uploadFile.raw
  if (!file) return
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (ext !== 'docx') {
    ElMessage.error('仅支持 .docx 检测报告')
    return
  }
  parsing.value = true
  try {
    const res = await phase2Api.parseCoaReport(file)
    const data = res.data || res
    if (data.error) {
      ElMessage.error(data.error)
      return
    }
    const batches: any[] = data.batches || []
    if (!batches.length) {
      ElMessage.warning('未从报告中解析到批次')
      return
    }
    // 多文件 → 合并 batches
    rows.value = [...rows.value, ...batches.map(testsToRow)]
    ElMessage.success(`已解析 ${batches.length} 个批次`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.error || '检测报告解析失败')
  } finally {
    parsing.value = false
  }
}

function toConfirmBatch(row: CoaBatchRow) {
  // 扁平字段优先（表格编辑），tests 保留以便后端提取 odour 等
  return {
    batch_no: row.batch_no,
    quantity_text: row.quantity_text,
    ph_label: row.ph_label,
    ph_spec: row.ph_spec,
    ph_result: row.ph_result,
    solid_label: row.solid_label,
    solid_spec: row.solid_spec,
    solid_result: row.solid_result,
    appearance_spec: row.appearance_spec,
    appearance_result: row.appearance_result,
    odour_label: row.odour_label,
    odour_spec: row.odour_spec,
    odour_result: row.odour_result,
    customer: row.customer,
    product_name_cn: row.product_name_cn,
    product_code: row.product_code,
    tests: row.tests,
  }
}

function onConfirm() {
  if (!rows.value.length) {
    ElMessage.warning('请先上传检测报告')
    return
  }
  loading.value = true
  try {
    emit('confirm', rows.value.map(toConfirmBatch))
    visible.value = false
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.coa-uploader {
  width: 100%;
  margin-bottom: 12px;
}
.coa-uploader :deep(.el-upload) {
  width: 100%;
}
.coa-uploader :deep(.el-upload-dragger) {
  padding: 24px 16px;
  border-radius: 12px;
  border: 2px dashed var(--el-border-color, #dcdfe6);
}
.batch-table-wrap {
  max-height: 360px;
  overflow: auto;
}
.batch-table-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
}
.batch-table {
  width: 100%;
}
.parsing-hint,
.empty-hint {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: 16px 0;
}
</style>
