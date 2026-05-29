<template>
  <div class="pi-preview-table">
    <!-- Header info + confidence -->
    <el-card class="header-card" shadow="never">
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="PI号">
          <el-input v-model="localData.pi_no" size="small" />
        </el-descriptions-item>
        <el-descriptions-item label="客户编码">
          <el-input v-model="localData.customer_code" size="small" />
        </el-descriptions-item>
        <el-descriptions-item label="业务员">
          <el-input v-model="localData.sales_person" size="small" />
        </el-descriptions-item>
        <el-descriptions-item label="日期">
          <el-input v-model="localData.pi_date" size="small" />
        </el-descriptions-item>
        <el-descriptions-item label="是否下单">
          <el-select v-model="localData.is_ordered" size="small" style="width: 100%">
            <el-option label="未下单" value="0" />
            <el-option label="已下单" value="1" />
          </el-select>
        </el-descriptions-item>
        <el-descriptions-item label="解析置信度">
          <el-tag :type="confidenceType" size="small">{{ localData.confidence.percentage }}</el-tag>
          <span v-if="localData.confidence.failed_rows > 0" class="failed-hint">
            ({{ localData.confidence.failed_rows }} 行失败)
          </span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- Editable items table -->
    <el-table :data="localData.items" border stripe size="small" class="items-table">
      <el-table-column label="#" width="50" type="index" />
      <el-table-column label="状态" width="70">
        <template #default="{ row }">
          <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
            {{ row.status === 'success' ? '✓' : '✗' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="内部编码" prop="internal_code" width="130">
        <template #default="{ row }">
          <el-input v-model="row.internal_code" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="数量" prop="quantity" width="110">
        <template #default="{ row }">
          <el-input-number v-model="row.quantity" size="small" :precision="2" :min="0" style="width: 100%" />
        </template>
      </el-table-column>
      <el-table-column label="单价" prop="unit_price" width="100">
        <template #default="{ row }">
          <el-input-number v-model="row.unit_price" size="small" :precision="2" :min="0" style="width: 100%" />
        </template>
      </el-table-column>
      <el-table-column label="金额" prop="total_amount" width="120">
        <template #default="{ row }">
          <span>{{ row.total_amount ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="产品颜色" prop="product_color" width="100">
        <template #default="{ row }">
          <el-input v-model="row.product_color" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="H.S.Code" prop="hs_code" width="130">
        <template #default="{ row }">
          <el-input v-model="row.hs_code" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="报关品名" prop="customs_name" min-width="160">
        <template #default="{ row }">
          <el-input v-model="row.customs_name" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="报关成分" prop="customs_composition" min-width="160">
        <template #default="{ row }">
          <el-input v-model="row.customs_composition" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="错误/缺失" min-width="200">
        <template #default="{ row }">
          <span v-if="row.status === 'error'" class="error-text">{{ row.error_msg }}</span>
          <span v-else-if="row._missing_fields?.length > 0" class="warning-text">
            缺失: {{ row._missing_fields.join(', ') }}
          </span>
        </template>
      </el-table-column>
    </el-table>

    <!-- Actions -->
    <div class="table-actions">
      <el-button @click="handleDownloadTemplate">下载标准模板</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        保存 PI 合同
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { savePiContract, type PiUploadResponse, type PiSaveRequest } from '@/api/pi'

const props = defineProps<{
  data: PiUploadResponse
}>()

const emit = defineEmits<{
  saved: [data: PiSaveRequest]
}>()

const saving = ref(false)
const localData = ref<PiUploadResponse>(JSON.parse(JSON.stringify(props.data)))

// Watch for prop changes to update local data
watch(() => props.data, (newData) => {
  localData.value = JSON.parse(JSON.stringify(newData))
}, { deep: true })

const confidenceType = computed(() => {
  const pct = parseInt(localData.value.confidence.percentage)
  if (pct >= 80) return 'success'
  if (pct >= 60) return 'warning'
  return 'danger'
})

const handleSave = async () => {
  saving.value = true
  try {
    const payload: PiSaveRequest = {
      pi_no: localData.value.pi_no,
      customer_code: localData.value.customer_code || undefined,
      sales_person: localData.value.sales_person || undefined,
      pi_date: localData.value.pi_date || undefined,
      is_ordered: localData.value.is_ordered,
      items: localData.value.items.map(item => ({
        internal_code: item.internal_code || '',
        quantity: item.quantity,
        unit_price: item.unit_price,
        total_amount: item.total_amount,
        product_color: item.product_color,
        hs_code: item.hs_code,
        customs_name: item.customs_name,
        customs_composition: item.customs_composition,
        order_customs_name: item.order_customs_name,
        notes: item.notes,
      })),
    }

    const response = await savePiContract(payload)
    ElMessage.success(response.message)
    emit('saved', payload)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleDownloadTemplate = () => {
  const headers = [
    '客户编码', 'PI号', '业务员', '日期', '销售订单号',
    '内部编码', '数量', '单价', '金额', '产品颜色',
    '海关编码', '报关品名', '报关成分', '填写订单报关品名', '是否下单', '文本'
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
</script>

<style scoped>
.pi-preview-table { margin-top: 0; }
.header-card { margin-bottom: 16px; }
.items-table { margin-bottom: 16px; }
.table-actions { display: flex; gap: 12px; justify-content: flex-end; }
.failed-hint { color: #e6a23c; font-size: 12px; margin-left: 6px; }
.error-text { color: #f56c6c; font-size: 12px; }
.warning-text { color: #e6a23c; font-size: 12px; }
</style>