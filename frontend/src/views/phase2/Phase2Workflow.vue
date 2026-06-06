<template>
  <div class="phase2">

    <!-- ── Toolbar ─────────────────────────────── -->
    <header class="toolbar">
      <div class="toolbar-left">
        <svg class="toolbar-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        <span class="toolbar-title">文档编辑</span>
      </div>

      <div class="toolbar-center">
        <div class="toolbar-field">
          <label class="toolbar-label">订单</label>
          <el-select
            v-model="selectedOrderId"
            placeholder="选择订单"
            size="small"
            class="toolbar-select"
            @change="onOrderChange"
            clearable
          >
            <template #empty>
              <span class="empty-hint">无已确认订单</span>
            </template>
            <el-option
              v-for="o in orderList"
              :key="o.id"
              :label="o.order_no + ' · ' + o.customer_code"
              :value="o.id"
            />
          </el-select>
        </div>

        <div class="toolbar-field" v-if="selectedOrderId">
          <label class="toolbar-label">PI合同</label>
          <el-select
            v-model="selectedPiNo"
            placeholder="选择PI"
            size="small"
            class="toolbar-select"
            clearable
          >
            <el-option
              v-for="p in piList"
              :key="p.pi_no"
              :label="p.pi_no"
              :value="p.pi_no"
            />
          </el-select>
        </div>
      </div>

      <div class="toolbar-actions">
        <el-button
          type="primary"
          size="small"
          :disabled="!selectedOrderId"
          @click="showBookingDialog = true"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
          </svg>
          订舱单
        </el-button>
        <el-button
          type="primary"
          size="small"
          :disabled="!selectedOrderId || !selectedPiNo"
          @click="openDocument('loi')"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
            <path d="M14 2H6a2 2 0 0 1 2v20a2 2 0 0 1-2 2H18a2 2 0 0 1-2-2V8l4-4z"/><path d="M14 2v6h6M16 13l4-4 4 4"/>
          </svg>
          LOI保函
        </el-button>
        <el-button size="small" @click="showMsdsDialog = true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M8 13h8M8 17h8M8 9h2"/>
          </svg>
          MSDS
        </el-button>
        <el-dropdown @command="(cmd: 'booking' | 'loi' | 'msds') => openBlankTemplate(cmd)" trigger="click">
          <el-button size="small">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
              <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
            </svg>
            空白模板
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="booking">📄 订舱单 Booking</el-dropdown-item>
              <el-dropdown-item command="loi">📝 LOI保函</el-dropdown-item>
              <el-dropdown-item command="msds">⚠️ MSDS物质安全表</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button size="small" @click="showMyDocuments = true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          我的模板
        </el-button>
      </div>
    </header>

    <!-- ── Main Layout: Left Info + Right Editor ── -->
    <div class="main-layout">
      <!-- Left: Info Panel -->
      <aside class="info-panel">
        <el-card class="info-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">订单信息</span>
              <el-tag v-if="currentOrderInfo.order_no" type="success" size="small">已选</el-tag>
            </div>
          </template>
          <div class="info-rows">
            <div class="info-row">
              <span class="info-label">发货人</span>
              <span class="info-value">HONGHAO CHEMICAL CO., LTD.</span>
            </div>
            <div class="info-row">
              <span class="info-label">收货人</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.consignee" size="small" placeholder="可编辑" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">通知人</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.notify" size="small" placeholder="可编辑" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">卸货港</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.port" size="small" placeholder="可编辑" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">品名中文</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.product_cn" size="small" placeholder="可编辑" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">品名英文</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.product_en" size="small" placeholder="可编辑" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">H.S.Code</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.hs_code" size="small" placeholder="可编辑" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">毛重</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.gross_weight" size="small" placeholder="可编辑">
                <template #append>kg</template>
              </el-input>
              <span v-else class="info-value muted">— kg</span>
            </div>
            <div class="info-row">
              <span class="info-label">体积(CBM)</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.volume" size="small" placeholder="可编辑">
                <template #append>m³</template>
              </el-input>
              <span v-else class="info-value muted">— m³</span>
            </div>
          </div>
        </el-card>

        <!-- Template Fields Reference -->
        <el-card class="info-card ref-card" shadow="never" style="margin-top: 12px;">
          <template #header>
            <div class="card-header">
              <span class="card-title">模板字段参考</span>
            </div>
          </template>
          <div class="ref-table">
            <div class="ref-row ref-header">
              <span>字段名</span>
              <span>含义</span>
            </div>
            <div class="ref-row">
              <code class="field-code">{{ 'MARK_SHIPPER' }}</code>
              <span class="field-desc">发货人 — 发货人公司名称</span>
            </div>
            <div class="ref-row">
              <code class="field-code">{{ 'MARK_PORT' }}</code>
              <span class="field-desc">卸货港 — 目的港/卸货港</span>
            </div>
            <div class="ref-row">
              <code class="field-code">{{ 'MARK_GOODS_TABLE' }}</code>
              <span class="field-desc">货物明细表 — 品名/规格/毛重/体积表格起始位</span>
            </div>
          </div>
        </el-card>
      </aside>

      <!-- Right: Document Editor / Workspace -->
      <main class="editor-panel">
        <!-- Workspace (no document open) -->
        <div v-if="!currentDocKey" class="workspace">
          <el-card class="preview-card">
            <template #header>
              <div class="card-header">
                <span class="card-title">快捷操作</span>
              </div>
            </template>
            <div class="workspace-actions">
              <el-button type="primary" size="large" :disabled="!selectedOrderId" @click="showBookingDialog = true" class="ws-btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px">
                  <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
                </svg>
                生成订舱单
              </el-button>
              <el-button type="primary" size="large" :disabled="!selectedOrderId || !selectedPiNo" @click="openDocument('loi')" class="ws-btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px">
                  <path d="M14 2H6a2 2 0 0 1 2v20a2 2 0 0 1-2 2H18a2 2 0 0 1-2-2V8l4-4z"/><path d="M14 2v6h6M16 13l4-4 4 4"/>
                </svg>
                生成LOI保函
              </el-button>
              <el-button size="large" @click="showMsdsDialog = true" class="ws-btn">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px">
                  <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M8 13h8M8 17h8M8 9h2"/>
                </svg>
                生成MSDS
              </el-button>
            </div>
          </el-card>

          <el-card class="preview-card" style="margin-top: 12px;">
            <template #header>
              <div class="card-header">
                <span class="card-title">我的模板</span>
                <el-button text size="small" @click="showMyDocuments = true">查看全部</el-button>
              </div>
            </template>
            <div class="recent-docs">
              <div class="empty-icon">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#d0d5dd" stroke-width="1.5">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                </svg>
              </div>
              <div class="recent-hint">暂无已保存的模板</div>
              <el-button type="primary" plain size="small" @click="showMyDocuments = true" style="margin-top: 8px;">浏览模板库</el-button>
            </div>
          </el-card>

          <el-card class="preview-card" style="margin-top: 12px;">
            <template #header>
              <div class="card-header">
                <span class="card-title">模板字段速查</span>
              </div>
            </template>
            <div class="ref-table">
              <div class="ref-row ref-header">
                <span>字段名</span>
                <span>含义</span>
              </div>
              <div class="ref-row">
                <code class="field-code">MARK_SHIPPER</code>
                <span class="field-desc">发货人</span>
              </div>
              <div class="ref-row">
                <code class="field-code">MARK_PORT</code>
                <span class="field-desc">卸货港</span>
              </div>
              <div class="ref-row">
                <code class="field-code">MARK_GOODS_TABLE</code>
                <span class="field-desc">货物明细表</span>
              </div>
              <div class="ref-row">
                <code class="field-code">MARK_CONSIGNEE</code>
                <span class="field-desc">收货人</span>
              </div>
              <div class="ref-row">
                <code class="field-code">MARK_NOTIFY</code>
                <span class="field-desc">通知人</span>
              </div>
            </div>
          </el-card>
        </div>

        <!-- Document Editor (when document is open) -->
        <div v-else class="doc-workspace">
          <DocumentEditor
            :key="currentDocKey"
            :document-server-url="currentConfig.documentServerUrl"
            :doc-key="currentDocKey"
            :token="currentConfig.token"
            :download-url="currentConfig.downloadUrl"
            :url="currentConfig.url"
            :doc-type="currentConfig.docType"
          />
        </div>
      </main>
    </div>

    <!-- ── Booking Dialog ────────────────────────── -->
    <el-dialog v-model="showBookingDialog" title="生成订舱单" width="380px" :append-to-body="true" class="booking-dialog">
      <div class="booking-select-row">
        <label class="booking-label">选择模板格式</label>
        <el-radio-group v-model="selectedBookingTemplate" size="default">
          <el-radio value="xlsx">.xlsx 格式（推荐，格式完整）</el-radio>
          <el-radio value="xls">.xls 格式（兼容旧版）</el-radio>
        </el-radio-group>
      </div>
      <template #footer>
        <el-button @click="showBookingDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmGenerateBooking">生成文档</el-button>
      </template>
    </el-dialog>

    <!-- ── MSDS Dialog ──────────────────────────── -->
    <el-dialog v-model="showMsdsDialog" title="生成 MSDS" width="440px" :append-to-body="true" class="msds-dialog">
      <div class="msds-select-row">
        <label class="msds-label">选择产品</label>
        <el-select v-model="selectedProductForMsds" placeholder="从当前订单选择产品" size="default" class="msds-select" clearable>
          <el-option v-for="item in currentOrderItems" :key="item.internal_code" :label="item.product_cn" :value="item.product_cn" />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="showMsdsDialog = false">取消</el-button>
        <el-button type="primary" @click="generateMsds" :disabled="!selectedProductForMsds">生成文档</el-button>
      </template>
    </el-dialog>

    <MyDocumentsDrawer v-model="showMyDocuments" @open-doc="onOpenMyDoc" />

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import DocumentEditor from './components/DocumentEditor.vue'
import MyDocumentsDrawer from './components/MyDocumentsDrawer.vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { phase2Api } from '@/api/phase2'
import { getOrderList, getOrderComparison, getOrderPiContracts, type OrderListItem } from '@/api/merge'

const route = useRoute()

const selectedOrderId = ref<number | null>(null)
const selectedPiNo = ref<string>('')
const orderList = ref<OrderListItem[]>([])
const piList = ref<any[]>([])
const currentOrderItems = ref<any[]>([])
const currentDocKey = ref('')
const currentConfig = ref<any>({})
const showMsdsDialog = ref(false)
const selectedProductForMsds = ref('')
const showMyDocuments = ref(false)
const showBookingDialog = ref(false)
const selectedBookingTemplate = ref<'xls' | 'xlsx'>('xlsx')

// Editable order info fields
const currentOrderInfo = ref({
  order_no: '',
  customer_code: '',
  consignee: '',
  notify: '',
  port: '',
  product_cn: '',
  product_en: '',
  hs_code: '',
  gross_weight: '',
  volume: '',
})

if (route.query.orderId) {
  selectedOrderId.value = Number(route.query.orderId)
}

async function loadOrderList() {
  const data = await getOrderList({ tab: 'completed', page_size: 100 })
  orderList.value = data.orders || []
}

async function onOrderChange(orderId: number) {
  selectedPiNo.value = ''
  if (!orderId) return
  try {
    const data = await getOrderComparison(orderId)
    currentOrderItems.value = data.items || []
    if (data.pi_no) selectedPiNo.value = data.pi_no
    const pis = await getOrderPiContracts(orderId)
    piList.value = pis
    if (pis.length > 0 && !selectedPiNo.value) {
      selectedPiNo.value = pis[0].pi_no
    }
    // Populate editable fields
    currentOrderInfo.value = {
      order_no: data.order_no || '',
      customer_code: data.customer_code || '',
      consignee: pis[0]?.consignee || '',
      notify: '',
      port: pis[0]?.destination || '',
      product_cn: data.items?.[0]?.product_cn || '',
      product_en: '',
      hs_code: data.items?.[0]?.order?.hs_code || '',
      gross_weight: '',
      volume: '',
    }
  } catch (e) {
    piList.value = []
  }
}

async function openDocument(type: 'booking' | 'loi') {
  if (type === 'booking') return
  try {
    const res = await phase2Api.generateLoi(selectedOrderId.value!, selectedPiNo.value)
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('文档生成失败: ' + (e.message || ''))
  }
}

async function confirmGenerateBooking() {
  showBookingDialog.value = false
  try {
    const res = await phase2Api.generateBooking(selectedOrderId.value!, selectedBookingTemplate.value)
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('订舱单生成失败: ' + (e.message || ''))
  }
}

async function generateMsds() {
  if (!selectedProductForMsds.value) return
  showMsdsDialog.value = false
  try {
    const res = await phase2Api.generateMsds(selectedProductForMsds.value)
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('MSDS生成失败: ' + (e.message || ''))
  }
}

async function openBlankTemplate(type: 'booking' | 'loi' | 'msds') {
  try {
    const res = await phase2Api.openBlankTemplate(type)
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('模板打开失败: ' + (e.message || ''))
  }
}

function onOpenMyDoc(doc: any) {
  showMyDocuments.value = false
  currentDocKey.value = doc.doc_key
  currentConfig.value = {
    token: doc.token,
    documentServerUrl: currentConfig.value.documentServerUrl,
    documentKey: doc.doc_key,
    downloadUrl: `/api/v1/onlyoffice/download/${encodeURIComponent(doc.doc_key)}`,
  }
}

onMounted(() => {
  loadOrderList()
  if (selectedOrderId.value) onOrderChange(selectedOrderId.value)
})
</script>

<style scoped>
/* ── Root ─────────────────────────────────────── */
.phase2 {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  min-height: 100vh;
  background: var(--el-bg-color-page, #f5f7fa);
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

/* ── Toolbar ─────────────────────────────────── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 56px;
  padding: 0 20px;
  background: var(--el-fill-color-lighter, #f5f7fa);
  border-bottom: 1px solid var(--el-border-color-light, #e4e7ed);
  flex-shrink: 0;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-primary, #303133);
  min-width: 100px;
}
.toolbar-icon { color: var(--el-color-primary, #409eff); flex-shrink: 0; }
.toolbar-title { font-size: 14px; font-weight: 600; letter-spacing: 0.02em; }
.toolbar-center {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}
.toolbar-field {
  display: flex;
  align-items: center;
  gap: 6px;
}
.toolbar-label {
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
  white-space: nowrap;
}
.toolbar-select { width: 200px; }
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* ── Main Layout ─────────────────────────── */
.main-layout {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 20px;
  align-items: start;
}

/* ── Info Panel (Left) ───────────────────── */
.info-panel {
  display: flex;
  flex-direction: column;
}

.info-card {
  border-radius: 8px;
  border: 1px solid var(--el-border-color-light, #e4e7ed);
}
:deep(.el-card__header) {
  padding: 10px 14px;
  background: var(--el-fill-color, #fff);
  border-bottom: 1px solid var(--el-border-color-light, #e4e7ed);
}
:deep(.el-card__body) {
  padding: 12px 14px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary, #303133);
  letter-spacing: 0.03em;
}

.info-rows {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.info-label {
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
  min-width: 80px;
  flex-shrink: 0;
}
.info-value {
  font-size: 12px;
  color: var(--el-text-color-primary, #303133);
}
.info-value.muted {
  color: var(--el-text-color-placeholder, #c0c4cc);
}
:deep(.info-row .el-input) {
  flex: 1;
}
:deep(.info-row .el-input__wrapper) {
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
}

/* ── Reference Card ────────────────────────── */
.ref-table {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ref-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 8px;
  font-size: 11px;
  align-items: start;
}
.ref-row.ref-header {
  font-weight: 600;
  color: var(--el-text-color-secondary, #909399);
  border-bottom: 1px solid var(--el-border-color-light, #e4e7ed);
  padding-bottom: 4px;
}
.field-code {
  font-family: 'JetBrains Mono', monospace;
  color: var(--el-color-primary, #409eff);
  background: var(--el-fill-color-light, #f5f7fa);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
}
.field-desc {
  color: var(--el-text-color-regular, #606266);
}

/* ── Editor Panel (Right) ───────────────────── */
.editor-panel {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 140px);
}

/* Workspace (no document open) */
.workspace {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 12px;
}
.workspace .preview-card {
  border-radius: 8px;
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  background: var(--el-fill-color, #fff);
}
:deep(.workspace .preview-card .el-card__header) {
  padding: 12px 16px;
  background: var(--el-fill-color-light, #f5f7fa);
  border-bottom: 1px solid var(--el-border-color-light, #e4e7ed);
}
:deep(.workspace .preview-card .el-card__body) {
  padding: 16px;
}

.workspace-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.ws-btn {
  height: 72px;
  font-size: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 8px;
  font-weight: 500;
}

.recent-hint {
  font-size: 13px;
  color: #909399;
  text-align: center;
  padding: 8px 0 4px 0;
}
.empty-icon {
  display: flex;
  justify-content: center;
  padding: 12px 0 4px 0;
}
.recent-docs {
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* Template field reference (workspace version) */
.workspace .ref-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.workspace .ref-row {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 12px;
  font-size: 13px;
  align-items: center;
}
.workspace .ref-row.ref-header {
  font-weight: 600;
  color: #909399;
  border-bottom: 1px solid var(--el-border-color-light, #e4e7ed);
  padding-bottom: 6px;
  font-size: 12px;
}
.workspace .field-code {
  font-family: 'JetBrains Mono', monospace;
  color: var(--el-color-primary, #409eff);
  background: var(--el-fill-color-light, #f5f7fa);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}
.workspace .field-desc {
  color: #606266;
  font-size: 13px;
}

/* Document workspace (editor open) */
.doc-workspace {
  flex: 1;
  display: flex;
  flex-direction: column;
}
:deep(.doc-workspace .el-card) {
  border-radius: 8px;
  flex: 1;
  display: flex;
  flex-direction: column;
}
:deep(.doc-workspace .el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0;
  min-height: 0;
}

/* ── Dialogs ─────────────────────────── */
.booking-select-row,
.msds-select-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 4px 0;
  flex-direction: column;
}
.booking-label,
.msds-label {
  font-size: 13px;
  color: var(--el-text-color-regular, #606266);
}

/* ── Scrollbar ──────────────────────────────── */
.info-panel::-webkit-scrollbar { width: 4px; }
.info-panel::-webkit-scrollbar-track { background: transparent; }
.info-panel::-webkit-scrollbar-thumb { background: #dcdfe6; border-radius: 2px; }
</style>
