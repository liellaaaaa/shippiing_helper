<template>
  <div class="land-transport-panel">
    <div class="panel-header">
      <h3>🚛 陆运总重计算</h3>
    </div>

    <div class="metric-cards">
      <el-card class="metric-card">
        <div class="metric-value">{{ result.total_drums }}</div>
        <div class="metric-label">总件数</div>
      </el-card>
      <el-card class="metric-card">
        <div class="metric-value">{{ result.total_weight_kg.toLocaleString() }}</div>
        <div class="metric-label">总毛重 (KG)</div>
      </el-card>
      <el-card class="metric-card">
        <div class="metric-value">{{ result.total_cbm.toFixed(2) }}</div>
        <div class="metric-label">总体积 (CBM)</div>
      </el-card>
    </div>

    <div class="overweight-warning" v-if="result.overweight_warning">
      <el-icon><WarningFilled /></el-icon>
      <span>⚠️ 总重超过 30 吨，部分国家公路限重规定，请注意安排。</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { WarningFilled } from '@element-plus/icons-vue'
import type { LandCalculationResult } from '@/api/packages'

defineProps<{
  result: LandCalculationResult
}>()
</script>

<style scoped>
.land-transport-panel { }
.panel-header { margin-bottom: 16px; }
.panel-header h3 { margin: 0; font-size: 16px; font-weight: 600; }

.metric-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.metric-card { text-align: center; }
.metric-value { font-size: 28px; font-weight: 700; color: #303133; }
.metric-label { font-size: 12px; color: #909399; margin-top: 4px; }

.overweight-warning { display: flex; align-items: center; gap: 8px; padding: 12px; background: #fef0f0; border: 1px solid #fbc4c4; border-radius: 6px; font-size: 13px; color: #f56c6c; }
</style>