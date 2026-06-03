<template>
  <div class="reference-panel">
    <el-collapse v-model="activeNames" accordion>

      <!-- Tab 1: Phase1数据 -->
      <el-collapse-item title="Phase1数据" name="phase1">
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
              <input
                v-model="phase1Data.notifyParty"
                class="field-input-editable"
                placeholder="可编辑"
              />
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
        </div>

        <div v-else class="empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".3">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
          </svg>
          <span>暂无数据</span>
        </div>
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
            <div
              v-for="m in currentMarkers"
              :key="m.marker"
              class="marker-row"
            >
              <code class="marker-code">{{ m.marker }}</code>
              <span>{{ m.label }} — {{ m.description }}</span>
            </div>
          </div>
        </div>
      </el-collapse-item>

      <!-- Tab 2: MSDS摘要 -->
      <el-collapse-item title="MSDS摘要" name="msds">
        <div v-if="msdsData" class="field-list">
          <div class="field-row"><div class="field-label">产品名称</div><div class="field-body field-body--readonly field-body--fill"><span class="field-value field-value--overflow">{{ msdsData.product_name_cn || '—' }}</span></div></div>
          <div class="field-row"><div class="field-label">物理形态</div><div class="field-body field-body--readonly"><span class="field-value">{{ msdsData.physical_form || '—' }}</span></div></div>
          <div class="field-row"><div class="field-label">离子类型</div><div class="field-body field-body--readonly"><span class="field-value">{{ msdsData.ion_type || '—' }}</span></div></div>
          <div class="field-row"><div class="field-label">pH值</div><div class="field-body field-body--readonly"><span class="field-value">{{ msdsData.ph || '—' }}</span></div></div>
        </div>
        <div v-else class="empty-state">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".3"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <span>未匹配MSDS</span>
        </div>
      </el-collapse-item>

      <!-- Tab 3: 运输鉴定报告 -->
      <el-collapse-item title="运输鉴定报告" name="transport">
        <div class="upload-zone" @click="triggerUpload" v-if="!transportData">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".5">
            <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 1 18 18h-1.61a2 2 0 0 1-2-2V9l-3-3H9a2 2 0 0 1-2-2v-.61A5 5 0 0 1 9 4.61L7.1 7.58a2 2 0 0 1-2.83 0L2.41 9.41A2 2 0 0 1 4.24 11.66l4.24 4.24a2 2 0 0 1 0 2.83L7.17 17.59a2 2 0 1 1 2.83 0l4.24-4.24"/>
          </svg>
          <span>点击上传运输鉴定报告 PDF</span>
          <em>拖拽 PDF 文件至此处</em>
        </div>
        <input ref="fileInput" type="file" accept=".pdf" style="display:none" @change="onFileSelected" />

        <div v-if="transportData" class="field-list">
          <div class="field-row"><div class="field-label field-label--editable">产品名称</div><div class="field-body field-body--editable"><input v-model="transportData.product_name" class="field-input-editable" placeholder="解析结果可修正" /></div></div>
          <div class="field-row"><div class="field-label field-label--editable">英文名</div><div class="field-body field-body--editable"><input v-model="transportData.english_name" class="field-input-editable" placeholder="解析结果可修正" /></div></div>
          <div class="field-row"><div class="field-label field-label--editable">报告编号</div><div class="field-body field-body--editable"><input v-model="transportData.report_number" class="field-input-editable" placeholder="解析结果可修正" /></div></div>
          <div class="field-row"><div class="field-label field-label--editable">样品描述</div><div class="field-body field-body--editable"><input v-model="transportData.sample_description" class="field-input-editable" placeholder="解析结果可修正" /></div></div>
        </div>
      </el-collapse-item>

      <!-- Tab 4: 出口商品编码 -->
      <el-collapse-item title="出口商品编码" name="exportcodes">
        <div class="search-box">
          <input v-model="exportCodeQuery" class="search-input" placeholder="输入商品内编查询" @keyup.enter="searchExportCodes" />
          <button class="search-btn" @click="searchExportCodes">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            查询
          </button>
        </div>
        <div v-if="exportCodeData" class="field-list">
          <div class="field-row"><div class="field-label">HS编码</div><div class="field-body field-body--readonly"><span class="field-value">{{ exportCodeData.hs_code || exportCodeData.export_hs_code || '—' }}</span></div></div>
          <div class="field-row"><div class="field-label">报关名称</div><div class="field-body field-body--readonly field-body--fill"><span class="field-value field-value--overflow">{{ exportCodeData.customs_name || '—' }}</span></div></div>
          <div class="field-row"><div class="field-label">成分</div><div class="field-body field-body--readonly field-body--fill"><span class="field-value field-value--overflow">{{ exportCodeData.composition || exportCodeData.components || '—' }}</span></div></div>
        </div>
        <div v-else class="empty-state">
          <span>无匹配结果</span>
        </div>
      </el-collapse-item>

    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Tickets } from '@element-plus/icons-vue'
import { phase2Api } from '@/api/phase2'
import { TEMPLATE_MARKERS } from '@/constants/template_markers'

const props = defineProps<{
  orderId: number | null
  productName: string
  internalCode: string
}>()

const SHIPPER_OPTIONS = [
  'HONGHAO CHEMICAL CO., LTD.',
  'HENGFA CHEMICAL CO., LTD.',
  'HONGYUAN CHEMICAL CO., LTD.',
]

const activeNames = ref(['phase1'])
const phase1Data = ref<Record<string, string>>({
  order_no: '', customer_code: '', consignee: '', port: '',
  product_name_cn: '', product_name_en: '', hs_code: '',
  gross_weight: '', volume: '', notifyParty: '',
})
const msdsData = ref<Record<string, string> | null>(null)
const transportData = ref<Record<string, string> | null>(null)
const exportCodeData = ref<Record<string, string> | null>(null)
const exportCodeQuery = ref('')
const shipperValue = ref(SHIPPER_OPTIONS[0])
const fileInput = ref<HTMLInputElement>()
const selectedTemplateType = ref('booking')
const currentMarkers = computed(() => TEMPLATE_MARKERS[selectedTemplateType.value] || [])

function triggerUpload() {
  fileInput.value?.click()
}

async function onFileSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const res = await phase2Api.uploadTransportReport(file)
  transportData.value = res.data
}

async function copy(text: string) {
  if (!text) return
  await navigator.clipboard.writeText(text)
  ElMessage.success('已复制')
}

watch(() => props.orderId, async (id) => {
  if (!id) return
  const res = await fetch(`/api/v1/merge/orders/${id}/comparison`)
  const data = await res.json()
  const first = data.items?.[0]
  phase1Data.value = {
    order_no: data.order_no || '',
    customer_code: data.customer_code || '',
    consignee: first?.pi?.consignee || first?.order?.consignee || '—',
    port: first?.pi?.port || '—',
    product_name_cn: first?.product_cn || '—',
    product_name_en: first?.order?.product_en || '—',
    hs_code: first?.order?.hs_code || '—',
    gross_weight: first?.order?.gross_weight != null ? String(first?.order?.gross_weight) : '—',
    volume: first?.order?.volume != null ? String(first?.order?.volume) : '—',
    notifyParty: '',
  }
}, { immediate: true })

watch(() => props.productName, async (name) => {
  if (!name) { msdsData.value = null; return }
  const res = await phase2Api.listMsds({ search: name, pageSize: 1 })
  msdsData.value = res.data.items?.[0] || null
}, { immediate: true })

watch(() => props.internalCode, (code) => {
  exportCodeQuery.value = code || ''
  if (code) searchExportCodes()
})

async function searchExportCodes() {
  if (!exportCodeQuery.value) return
  const res = await phase2Api.getExportCodes(exportCodeQuery.value)
  exportCodeData.value = res.data.error ? null : res.data
}
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

/* ── Search box ─────────────────────────────────────── */
.search-box {
  display: flex;
  gap: 8px;
  padding: 12px 12px 0;
  margin-bottom: 4px;
}
.search-input {
  flex: 1;
  height: 32px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  padding: 0 10px;
  font-size: 13px;
  outline: none;
  background: var(--el-fill-color-light);
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.search-input:focus {
  border-color: var(--el-color-primary);
  background: #fff;
}
.search-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  padding: 0 14px;
  border: none;
  border-radius: 4px;
  background: var(--el-color-primary);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.15s;
}
.search-btn:hover { opacity: 0.85; }

/* ── Upload zone ──────────────────────────────────────── */
.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 90px;
  margin: 12px 12px 0;
  border: 1.5px dashed var(--el-border-color);
  border-radius: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}
.upload-zone:hover { border-color: var(--el-color-primary); color: var(--el-color-primary); }
.upload-zone em { font-style: normal; color: var(--el-text-color-placeholder); font-size: 11px; }

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

/* ── el-collapse overrides ─────────────────────────────── */
:deep(.el-collapse-item__header) {
  font-size: 13px;
  font-weight: 500;
  padding-left: 12px;
  background: var(--el-fill-color-lighter);
}
:deep(.el-collapse-item__content) {
  padding: 0;
}
:deep(.el-collapse-item__wrap) {
  border-bottom: none;
}
:deep(.el-collapse-item:last-child .el-collapse-item__header) {
  border-bottom: 1px solid var(--el-border-color-light);
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
</style>
