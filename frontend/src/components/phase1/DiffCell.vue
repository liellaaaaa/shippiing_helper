<template>
  <div class="diff-cell">
    <span v-if="!hasDiff" class="一致">✅ 一致</span>
    <el-tooltip
      v-else
      placement="top"
      :content="tooltipContent"
    >
      <span :class="cellClass">{{ displayValue }} <span class="diff-flag">⚠️</span></span>
    </el-tooltip>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  orderValue?: number | string
  piValue?: number | string
  diffStatus: string  // "一致" / "数量不符" / "PI未覆盖" 等
  flags: string[]
}>()

const hasDiff = computed(() => props.flags.length > 0 || props.diffStatus === 'PI未覆盖')

const displayValue = computed(() => {
  if (props.diffStatus === 'PI未覆盖') return '—'
  return props.orderValue !== undefined ? String(props.orderValue) : '—'
})

const cellClass = computed(() => {
  if (props.diffStatus === 'PI未覆盖') return 'pi-missing'
  return 'diff-warning'
})

const tooltipContent = computed(() => {
  if (props.diffStatus === 'PI未覆盖') {
    return `订单有数据，PI 未覆盖此产品`
  }
  return `订单值：${props.orderValue ?? '-'} / PI值：${props.piValue ?? '-'}`
})
</script>

<style scoped>
.diff-cell { font-size: 13px; }
.一致 { color: #67c23a; }
.diff-warning { color: #f56c6c; cursor: pointer; }
.pi-missing { color: #e6a23c; cursor: pointer; }
.diff-flag { margin-left: 2px; }
</style>