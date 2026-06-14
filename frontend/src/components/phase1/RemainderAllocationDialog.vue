<template>
  <el-dialog
    v-model="visible"
    title="余数桶分配"
    width="560px"
    :append-to-body="true"
    class="remainder-allocation-dialog"
    @closed="onClosed"
  >
    <div class="dialog-tip">
      以下产品存在余数桶，请选择处理方式：
    </div>

    <el-table :data="rows" border size="small" class="remainder-table">
      <el-table-column label="产品" prop="product_name" min-width="120" />
      <el-table-column label="桶数" prop="drums" width="70" align="center" />
      <el-table-column label="每板桶数" prop="drums_per_pallet" width="90" align="center" />
      <el-table-column label="余数" width="70" align="center">
        <template #default="{ row }">
          <span class="remainder-num">{{ row.remainder }}</span>
        </template>
      </el-table-column>
      <el-table-column label="分配方式" min-width="200">
        <template #default="{ row }">
          <el-radio-group v-model="row.remainder_allocated" size="small">
            <el-radio-button value="own_pallet">单独放卡板</el-radio-button>
            <el-radio-button value="pending">搁置待拼板</el-radio-button>
          </el-radio-group>
        </template>
      </el-table-column>
    </el-table>

    <div class="dialog-summary">
      <span>总待处理余数桶：<strong>{{ totalRemainder }}</strong> 个</span>
      <span v-if="ownPalletCount > 0">，将新增 <strong>{{ ownPalletCount }}</strong> 个卡板</span>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :disabled="!allAllocated" @click="onConfirm">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

export interface RemainderRow {
  id: string
  product_name: string
  drums: number
  drums_per_pallet: number
  remainder: number
  remainder_allocated: 'own_pallet' | 'pending' | null
}

const props = defineProps<{
  modelValue: boolean
  rows: RemainderRow[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'confirm': [rows: RemainderRow[]]
}>()

const visible = ref(props.modelValue)

watch(() => props.modelValue, (v) => {
  visible.value = v
})
watch(visible, (v) => emit('update:modelValue', v))

const totalRemainder = computed(() =>
  props.rows.reduce((sum, r) => sum + (r.remainder || 0), 0)
)

const ownPalletCount = computed(() =>
  props.rows.filter(r => r.remainder_allocated === 'own_pallet').length
)

const allAllocated = computed(() =>
  props.rows.every(r => r.remainder_allocated !== null)
)

function onConfirm() {
  emit('confirm', [...props.rows])
  visible.value = false
}

function onClosed() {
  // reset allocation choices
  props.rows.forEach(r => {
    r.remainder_allocated = null
  })
}
</script>

<style scoped>
.dialog-tip {
  font-size: 13px;
  color: #909399;
  margin-bottom: 12px;
}
.remainder-table {
  margin-bottom: 12px;
}
.remainder-num {
  color: #e6a23c;
  font-weight: 600;
}
.dialog-summary {
  font-size: 13px;
  color: #606266;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}
</style>