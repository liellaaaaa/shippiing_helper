<template>
  <el-dialog
    v-model="visible"
    title="批量生成MSDS"
    width="800px"
    :append-to-body="true"
    @closed="onClosed"
  >
    <div class="batch-info">
      <el-alert type="info" :closable="false" show-icon>
        已选择 <strong>{{ items.length }}</strong> 个产品，每个产品将生成中文和英文两个MSDS文件
      </el-alert>
    </div>

    <el-table :data="items" size="small" style="width: 100%; margin: 16px 0" max-height="400">
      <el-table-column prop="customs_name" label="产品名称" width="140" />
      <el-table-column label="外观" width="120" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.appearance || '无资料' }}
        </template>
      </el-table-column>
      <el-table-column label="MSDS编号" width="160">
        <template #default="{ row }">
          <el-input
            v-model="row._msds_number"
            size="small"
            placeholder="HHJS-XXXX"
          />
        </template>
      </el-table-column>
      <el-table-column label="修订时间" width="180">
        <template #default="{ row }">
          <el-date-picker
            v-model="row._revision_date"
            type="date"
            size="small"
            format="YYYY/MM/DD"
            value-format="YYYY/MM/DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </template>
      </el-table-column>
      <el-table-column label="版次" width="120">
        <template #default="{ row }">
          <el-input
            v-model="row._revision"
            size="small"
            placeholder="YYYY-MM"
          />
        </template>
      </el-table-column>
      <el-table-column label="更新日期" width="120">
        <template #default="{ row }">
          <el-input
            v-model="row._update_date"
            size="small"
            placeholder="YYYY年MM月"
          />
        </template>
      </el-table-column>
    </el-table>

    <div v-if="errors.length > 0" class="error-section">
      <el-alert type="error" :closable="false" show-icon>
        <template #title>
          {{ errors.length }} 个产品生成失败
        </template>
        <div class="error-list">
          <div v-for="(err, idx) in errors" :key="idx" class="error-item">
            {{ err.product_name }}: {{ err.message }}
          </div>
        </div>
      </el-alert>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="generating" @click="onConfirm">
        确认生成 ({{ items.length }}个产品 × 2 = {{ items.length * 2 }}个文件)
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { msdsLedgerApi, type MsdsLedgerItem } from '@/api/msds-ledger'

interface BatchItem extends MsdsLedgerItem {
  _msds_number: string
  _revision_date: string
  _revision: string
  _update_date: string
}

const props = defineProps<{ modelValue: boolean; selectedItems: MsdsLedgerItem[] }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'generated': []
}>()

const visible = ref(props.modelValue)
const generating = ref(false)
const items = ref<BatchItem[]>([])
const errors = ref<{ product_name: string; message: string }[]>([])

watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v) {
    errors.value = []
    items.value = props.selectedItems.map(item => ({
      ...item,
      _msds_number: generateMsdsNumber(),
      _revision_date: getDefaultDate(),
      _revision: '',
      _update_date: '',
    }))
    // Auto-fill revision and update_date
    for (const item of items.value) {
      updateDerivedFields(item)
    }
  }
})

function getDefaultDate() {
  const d = new Date()
  d.setMonth(d.getMonth() - 2)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}/${m}/${day}`
}

function generateMsdsNumber() {
  const year = String(new Date().getFullYear()).slice(-2)
  const monthOffset = Math.floor(Math.random() * 3) + 3
  const d = new Date()
  d.setMonth(d.getMonth() - monthOffset)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  return `HHJS-${year}${mm}`
}

function updateDerivedFields(item: BatchItem) {
  if (item._revision_date) {
    const parts = item._revision_date.split('/')
    if (parts.length >= 2) {
      item._revision = `${parts[0]}-${parts[1]}`
      item._update_date = `${parts[0]}年${parseInt(parts[1])}月`
    }
  }
}

// Watch for revision_date changes to update derived fields
watch(items, (newItems) => {
  for (const item of newItems) {
    updateDerivedFields(item)
  }
}, { deep: true })

async function onConfirm() {
  if (items.value.length === 0) {
    ElMessage.warning('请至少选择一个产品')
    return
  }

  generating.value = true
  errors.value = []

  try {
    const overrides: Record<string, { msds_number: string; revision_date: string }> = {}
    for (const item of items.value) {
      overrides[String(item.id)] = {
        msds_number: item._msds_number,
        revision_date: item._revision_date,
      }
    }

    const res = await msdsLedgerApi.batchGenerate({
      ledger_ids: items.value.map(i => i.id),
      overrides,
    })

    // Download ZIP
    const blob = new Blob([res.data], { type: 'application/zip' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `MSDS_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}_${items.value.length}个产品.zip`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    ElMessage.success(`已生成 ${items.value.length} 个产品的MSDS`)
    emit('generated')
    visible.value = false
  } catch (e: any) {
    ElMessage.error('批量生成失败: ' + (e.message || ''))
  } finally {
    generating.value = false
  }
}

function onClosed() {
  items.value = []
  errors.value = []
}
</script>

<style scoped>
.batch-info {
  margin-bottom: 8px;
}
.error-section {
  margin-top: 16px;
}
.error-list {
  margin-top: 8px;
}
.error-item {
  font-size: 12px;
  color: var(--el-color-danger);
  margin: 4px 0;
}
</style>
