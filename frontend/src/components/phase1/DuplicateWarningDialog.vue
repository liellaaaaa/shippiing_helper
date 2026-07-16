<template>
  <el-dialog
    v-model="visible"
    title="检测到重复产品"
    width="680px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    @close="handleCancel"
  >
    <el-alert type="warning" :closable="false" style="margin-bottom: 16px">
      以下 <strong>{{ duplicates.length }}</strong> 个产品已存在于台账中，重复入库会导致数据冗余。
    </el-alert>

    <el-table :data="duplicates" border stripe size="small" max-height="300">
      <el-table-column prop="internal_code" label="内编" width="110" />
      <el-table-column prop="customs_name" label="报关名" min-width="130" show-overflow-tooltip />
      <el-table-column prop="hs_code" label="H.S.Code" width="110" />
      <el-table-column prop="components" label="成分" min-width="120" show-overflow-tooltip />
      <el-table-column prop="product_appearance" label="外观" width="90" />
      <el-table-column prop="existing_order_no" label="已入库订单号" width="140" />
    </el-table>

    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" @click="handleViewDashboard">去数据中心查看</el-button>
      <el-button type="danger" @click="handleConfirm">仍然入库</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { DuplicateItem } from '@/api/orders'

const props = defineProps<{
  modelValue: boolean
  duplicates: DuplicateItem[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const router = useRouter()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

function handleConfirm() {
  emit('update:modelValue', false)
  emit('confirm')
}

function handleCancel() {
  emit('update:modelValue', false)
  emit('cancel')
}

function handleViewDashboard() {
  emit('update:modelValue', false)
  router.push({ path: '/dashboard' })
}
</script>
