<template>
  <div class="air-freight-panel">
    <div class="panel-header">
      <h3>✈️ 空运计费重量计算</h3>
    </div>

    <div class="weight-cards">
      <el-card class="weight-card actual">
        <div class="weight-value">{{ result.actual_weight_kg.toLocaleString() }}</div>
        <div class="weight-label">📏 物理实重 (KG)</div>
        <div class="weight-note">灰色基准参考值</div>
      </el-card>

      <el-card class="weight-card iata">
        <div class="weight-value">{{ result.vol_weight_167.toLocaleString() }}</div>
        <div class="weight-label">✈️ IATA 标准 (×167)</div>
        <div class="weight-note">国际通用标准</div>
      </el-card>

      <el-card class="weight-card airline">
        <div class="weight-value">{{ result.vol_weight_6000.toLocaleString() }}</div>
        <div class="weight-label">📦 航司标准 (÷6000)</div>
        <div class="weight-note">部分航司标准</div>
      </el-card>

      <el-card class="weight-card chargeable" :class="{ highlight: isHighlighted }">
        <div class="weight-value">{{ result.chargeable_weight_kg.toLocaleString() }}</div>
        <div class="weight-label">⚖️ 计费重量 (KG)</div>
        <div class="weight-note">最终付费依据 — {{ result.chargeable_weight_note }}</div>
      </el-card>
    </div>

    <div class="warning-tip">
      <el-icon><Warning /></el-icon>
      <span>⚠️ 实际计费重量取决于您合作的货代或航空公司报价条款，请以最终确认的系数为准。</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Warning } from '@element-plus/icons-vue'
import type { AirCalculationResult } from '@/api/packages'

const props = defineProps<{
  result: AirCalculationResult
}>()

const isHighlighted = computed(() => {
  return props.result.chargeable_weight_kg === props.result.actual_weight_kg
})
</script>

<style scoped>
.air-freight-panel { }
.panel-header { margin-bottom: 16px; }
.panel-header h3 { margin: 0; font-size: 16px; font-weight: 600; }

.weight-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.weight-card { text-align: center; }
.weight-card.actual .weight-value { color: #909399; }
.weight-card.iata .weight-value { color: #67c23a; }
.weight-card.airline .weight-value { color: #409eff; }
.weight-card.chargeable .weight-value { color: #f56c6c; }
.weight-card.chargeable.highlight { border: 2px solid #f56c6c; }
.weight-value { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
.weight-label { font-size: 13px; font-weight: 500; margin-bottom: 2px; }
.weight-note { font-size: 11px; color: #909399; }

.warning-tip { display: flex; align-items: center; gap: 8px; padding: 12px; background: #fdf6ec; border: 1px solid #f5dab1; border-radius: 6px; font-size: 13px; color: #e6a23c; }
</style>