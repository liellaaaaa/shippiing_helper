<template>
  <div class="reference-panel">
    <!-- Phase1数据 -->
    <div v-if="phase1Data" class="field-list">
      <!-- 发货人：select 可切换发货主体 -->
      <div class="field-row">
        <div class="field-label">发货人</div>
        <div class="field-body field-body--select">
          <el-select
            v-model="shipperValue"
            placeholder="选择发货人"
            filterable
            allow-create
            default-first-option
            size="small"
          >
            <el-option v-for="s in SHIPPER_OPTIONS" :key="s" :label="s" :value="s" />
          </el-select>
        </div>
        <button class="field-copy" @click="copy(shipperValue)" title="复制">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>

      <!-- 收货人（只读） -->
      <div class="field-row">
        <div class="field-label">收货人</div>
        <div class="field-body field-body--readonly">
          <span class="field-value">{{ phase1Data.consignee || '—' }}</span>
        </div>
        <button class="field-copy" @click="copy(phase1Data.consignee)" title="复制">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>

      <!-- 通知人（可编辑） -->
      <div class="field-row">
        <div class="field-label field-label--editable">通知人</div>
        <div class="field-body field-body--editable">
          <input v-model="phase1Data.notifyParty" class="field-input-editable" placeholder="可编辑" />
        </div>
        <button class="field-copy" @click="copy(phase1Data.notifyParty)" title="复制">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>

      <!-- 卸货港（只读） -->
      <div class="field-row">
        <div class="field-label">卸货港</div>
        <div class="field-body field-body--readonly">
          <span class="field-value">{{ phase1Data.port || '—' }}</span>
        </div>
        <button class="field-copy" @click="copy(phase1Data.port)" title="复制">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>

      <!-- 品名中文（只读） -->
      <div class="field-row">
        <div class="field-label">品名中文</div>
        <div class="field-body field-body--readonly field-body--fill">
          <span class="field-value field-value--overflow" :title="phase1Data.product_name_cn">{{ phase1Data.product_name_cn || '—' }}</span>
        </div>
        <button class="field-copy" @click="copy(phase1Data.product_name_cn)" title="复制">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>

      <!-- 品名英文（只读） -->
      <div class="field-row">
        <div class="field-label">品名英文</div>
        <div class="field-body field-body--readonly field-body--fill">
          <span class="field-value field-value--overflow" :title="phase1Data.product_name_en">{{ phase1Data.product_name_en || '—' }}</span>
        </div>
        <button class="field-copy" @click="copy(phase1Data.product_name_en)" title="复制">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>

      <!-- H.S.Code（只读） -->
      <div class="field-row">
        <div class="field-label">H.S.Code</div>
        <div class="field-body field-body--readonly">
          <span class="field-value">{{ phase1Data.hs_code || '—' }}</span>
        </div>
        <button class="field-copy" @click="copy(phase1Data.hs_code)" title="复制">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>

      <!-- 毛重（只读） -->
      <div class="field-row">
        <div class="field-label">毛重</div>
        <div class="field-body field-body--readonly">
          <span class="field-value">{{ phase1Data.gross_weight || '—' }} kg</span>
        </div>
        <button class="field-copy" @click="copy(phase1Data.gross_weight)" title="复制">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>

      <!-- 体积（只读） -->
      <div class="field-row">
        <div class="field-label">体积(CBM)</div>
        <div class="field-body field-body--readonly">
          <span class="field-value">{{ phase1Data.volume || '—' }} m³</span>
        </div>
        <button class="field-copy" @click="copy(phase1Data.volume)" title="复制">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
        </button>
      </div>

      <!-- 多产品列表 -->
      <div v-if="productsList.length > 1" class="products-list">
        <div class="products-list-header">产品明细（共 {{ productsList.length }} 种）</div>
        <div v-for="(p, idx) in productsList" :key="idx" class="product-item">
          <div class="product-item-name">{{ p.product_cn }}</div>
          <div class="product-item-detail">
            <span>{{ p.spec_kg }}kg/件</span>
            <span>×</span>
            <span>{{ p.quantity_kg }}kg</span>
            <span>·</span>
            <span>{{ p.gross_weight }}kg</span>
            <span>·</span>
            <span>{{ p.volume.toFixed(3) }}m³</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".3">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
      </svg>
      <span>暂无数据</span>
    </div>

    <!-- 模板字段参考（无订单时显示） -->
    <div v-if="!orderId" class="marker-guide">
      <div class="marker-guide-header">
        <el-icon><tickets /></el-icon>
        <span>模板字段参考</span>
        <el-select v-model="selectedTemplateType" size="small" class="template-type-select">
          <el-option label="订舱单" value="booking" />
          <el-option label="LOI保函" value="loi" />
          <el-option label="MSDS" value="msds" />
        </el-select>
      </div>
      <div class="marker-table">
        <div class="marker-row marker-row--header">
          <span>字段名</span><span>含义</span>
        </div>
        <div v-for="m in currentMarkers" :key="m.marker" class="marker-row">
          <code class="marker-code">{{ m.marker }}</code>
          <span>{{ m.label }} — {{ m.description }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Tickets } from '@element-plus/icons-vue'
import { TEMPLATE_MARKERS } from '@/constants/template_markers'

const props = defineProps<{
  orderId: number | null
}>()

const SHIPPER_OPTIONS = [
  'HONGHAO CHEMICAL CO., LTD.',
  'HENGFA CHEMICAL CO., LTD.',
  'HONGYUAN CHEMICAL CO., LTD.',
]

const phase1Data = ref<Record<string, string>>({
  order_no: '', customer_code: '', consignee: '', port: '',
  product_name_cn: '', product_name_en: '', hs_code: '',
  gross_weight: '', volume: '', notifyParty: '',
})
// 多产品列表
const productsList = ref<Array<{
  product_cn: string
  spec_kg: number
  quantity_kg: number
  gross_weight: number
  volume: number
}>>([])
const shipperValue = ref(SHIPPER_OPTIONS[0])
const selectedTemplateType = ref('booking')
const currentMarkers = computed(() => TEMPLATE_MARKERS[selectedTemplateType.value] || [])

async function copy(text: string) {
  if (!text) return
  await navigator.clipboard.writeText(text)
  ElMessage.success('已复制')
}

watch(() => props.orderId, async (id) => {
  if (!id) {
    phase1Data.value = { order_no: '', customer_code: '', consignee: '', port: '', product_name_cn: '', product_name_en: '', hs_code: '', gross_weight: '', volume: '', notifyParty: '' }
    productsList.value = []
    return
  }
  const res = await fetch(`/api/v1/merge/orders/${id}/comparison`)
  const data = await res.json()
  const first = data.items?.[0]

  // 汇总多产品信息
  const allItems = data.items || []
  const totalGw = allItems.reduce((s: number, item: any) => s + (item.order?.gross_weight || 0), 0)
  const totalVol = allItems.reduce((s: number, item: any) => s + (item.order?.volume || 0), 0)
  const productNames = allItems.map((i: any) => i.product_cn).filter(Boolean).join(' / ')

  phase1Data.value = {
    order_no: data.order_no || '',
    customer_code: data.customer_code || '',
    consignee: first?.pi?.consignee || first?.order?.consignee || '—',
    port: first?.pi?.port || '—',
    product_name_cn: productNames || (first?.product_cn || '—'),
    product_name_en: first?.order?.product_en || '—',
    hs_code: first?.order?.hs_code || '—',
    gross_weight: totalGw > 0 ? String(Math.round(totalGw)) : (first?.order?.gross_weight != null ? String(first?.order?.gross_weight) : '—'),
    volume: totalVol > 0 ? String(totalVol.toFixed(3)) : (first?.order?.volume != null ? String(first?.order?.volume) : '—'),
    notifyParty: '',
  }

  // 构建多产品列表
  productsList.value = allItems.map((item: any) => ({
    product_cn: item.product_cn || '—',
    spec_kg: item.order?.spec_kg || 0,
    quantity_kg: item.order?.quantity || 0,
    gross_weight: item.order?.gross_weight || 0,
    volume: item.order?.volume || 0,
  }))
}, { immediate: true })
</script>

<style scoped>
/* ── Layout ─────────────────────────────────────────────── */
.reference-panel { height: 100%; overflow-y: auto; background: var(--el-bg-color); }

/* ── Row system ─────────────────────────────────────────── */
/* 每行固定 40px，label 80px，body 填满剩余，copy-btn 36px */
.field-list { display: flex; flex-direction: column; gap: 0; }

.field-row {
  display: grid;
  grid-template-columns: 88px 1fr 36px;
  align-items: center;
  height: 40px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  padding: 0 12px;
  gap: 8px;
}
.field-row:last-child { border-bottom: none; }

/* ── Label ──────────────────────────────────────────────── */
.field-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
  line-height: 1;
  /* editable label gets a left accent bar */
}
.field-label--editable {
  color: var(--el-color-primary);
  position: relative;
  padding-left: 6px;
}
.field-label--editable::before {
  content: '';
  position: absolute;
  left: 0; top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 14px;
  background: var(--el-color-primary-light-3, #409eff);
  border-radius: 1px;
}

/* ── Body ─────────────────────────────────────────────── */
.field-body {
  min-width: 0;
  height: 100%;
  display: flex;
  align-items: center;
}
.field-body--readonly {
  color: var(--el-text-color-primary);
  font-size: 13px;
}
.field-body--fill { flex: 1; }
.field-body--select .el-select { width: 100%; }
.field-body--select .el-select .el-input__wrapper { border-radius: 4px; }
.field-body--editable { }

/* ── Value text ────────────────────────────────────────────── */
.field-value {
  font-size: 13px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.field-value--overflow {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Copy button ───────────────────────────────────────── */
.field-copy {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--el-color-info-light-3, #909399);
  cursor: pointer;
  border-radius: 4px;
  transition: color 0.15s, background 0.15s;
  flex-shrink: 0;
}
.field-copy:hover {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9, #ecf5ff);
}

/* ── Editable native input (通知人 / 运输鉴定 / 出口编码搜索) ─── */
.field-input-editable {
  width: 100%;
  height: 32px;
  border: 1px solid var(--el-border-color, #dcdfe6);
  border-radius: 4px;
  padding: 0 10px;
  font-size: 13px;
  font-family: inherit;
  background: var(--el-fill-color-light, #f5f7fa);
  color: var(--el-text-color-primary);
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}
.field-input-editable:focus {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15);
  background: #fff;
}
.field-input-editable::placeholder { color: var(--el-text-color-placeholder, #c0c4cc); }

/* ── Empty state ─────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 80px;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}

/* ── el-select small size ─────────────────────────────── */
:deep(.el-select--small .el-input__wrapper) {
  border-radius: 4px;
}
:deep(.el-select--small .el-select__wrapper) {
  min-height: 32px;
  height: 32px;
}

/* ── Marker Guide ──────────────────────────────── */
.marker-guide {
  margin: 0 12px 12px;
  border: 1px solid var(--el-border-color-extra-light);
  border-radius: 8px;
  overflow: hidden;
}
.marker-guide-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.template-type-select { margin-left: auto; width: 100px; }
.marker-table { font-size: 11px; }
.marker-row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 8px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  align-items: center;
}
.marker-row:last-child { border-bottom: none; }
.marker-row--header {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-secondary);
  font-size: 11px;
  padding: 4px 12px;
}
.marker-code {
  font-family: 'JetBrains Mono', monospace;
  color: var(--el-color-primary);
  font-size: 11px;
  background: var(--el-color-primary-light-9);
  padding: 1px 4px;
  border-radius: 3px;
}

/* ── Products List ──────────────────────────────── */
.products-list {
  border-top: 1px solid var(--el-border-color-extra-light);
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
}
.products-list-header {
  font-size: 11px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}
.product-item {
  padding: 4px 0;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.product-item:last-child { border-bottom: none; }
.product-item-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  margin-bottom: 2px;
}
.product-item-detail {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
</style>
