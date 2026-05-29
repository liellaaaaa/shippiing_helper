<template>
  <el-dialog
    v-model="visible"
    title="编辑列映射"
    width="650px"
    :close-on-click-modal="false"
  >
    <div class="mapping-tip">
      <el-alert type="warning" :closable="false" show-icon>
        <template #title>
          识别率较低 ({{ confidencePercent }}%)，请为未识别的列选择对应的目标字段
        </template>
      </el-alert>
    </div>

    <el-table :data="mappingRows" border size="small" class="mapping-table">
      <el-table-column label="原始列名" prop="original" min-width="150" />
      <el-table-column label="目标字段" min-width="180">
        <template #default="{ row }">
          <el-select v-model="row.target" placeholder="选择字段" clearable size="small">
            <el-option
              v-for="field in targetFields"
              :key="field.value"
              :label="field.label"
              :value="field.value"
            />
          </el-select>
        </template>
      </el-table-column>
    </el-table>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleApply">应用映射</el-button>
      <el-button @click="handleSaveTemplate">保存为客户模板</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface MappingRow {
  original: string
  target: string
  index: number
}

const props = defineProps<{
  confidencePercent: string
  originalColumns?: string[]
}>()

const emit = defineEmits<{
  apply: [mapping: Record<string, string>]
  saveTemplate: [mapping: Record<string, string>]
}>()

const visible = ref(true)

const targetFields = [
  { value: 'customer_code', label: '客户编码' },
  { value: 'pi_no', label: 'PI号' },
  { value: 'sales_person', label: '业务员' },
  { value: 'pi_date', label: '日期' },
  { value: 'order_id', label: '销售订单号' },
  { value: 'internal_code', label: '内部编码' },
  { value: 'quantity', label: '数量' },
  { value: 'unit_price', label: '单价' },
  { value: 'total_amount', label: '金额' },
  { value: 'product_color', label: '产品颜色' },
  { value: 'hs_code', label: '海关编码' },
  { value: 'customs_name', label: '报关品名' },
  { value: 'customs_composition', label: '报关成分' },
  { value: 'order_customs_name', label: '填写订单报关品名' },
  { value: 'is_ordered', label: '是否下单' },
  { value: 'notes', label: '备注' },
]

// Initialize mapping rows - one per original column
const mappingRows = ref<MappingRow[]>(
  (props.originalColumns || []).map((col, idx) => ({
    original: col,
    target: '',
    index: idx,
  }))
)

const handleApply = () => {
  const mapping: Record<string, string> = {}
  mappingRows.value.forEach(row => {
    if (row.target) {
      mapping[row.original] = row.target
    }
  })
  emit('apply', mapping)
  visible.value = false
}

const handleSaveTemplate = () => {
  const mapping: Record<string, string> = {}
  mappingRows.value.forEach(row => {
    if (row.target) {
      mapping[row.original] = row.target
    }
  })
  emit('saveTemplate', mapping)
  ElMessage.success('模板保存成功')
  visible.value = false
}
</script>

<style scoped>
.mapping-tip { margin-bottom: 16px; }
.mapping-table { max-height: 400px; overflow-y: auto; }
</style>