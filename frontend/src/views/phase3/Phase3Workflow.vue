<template>
  <div class="phase3">

    <!-- ── Toolbar ─────────────────────────────── -->
    <header class="toolbar">
      <div class="toolbar-left">
        <svg class="toolbar-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 11l3 3L22 4"/>
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
        </svg>
        <span class="toolbar-title">报关资料编辑</span>
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
              :key="o.order_id"
              :label="o.order_no + ' · ' + o.customer_code"
              :value="o.order_id"
            />
          </el-select>
        </div>
      </div>

      <div class="toolbar-actions">
        <el-button
          type="primary"
          size="small"
          :disabled="!selectedOrderId"
          @click="openCustoms"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
            <path d="M9 11l3 3L22 4"/>
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
          </svg>
          报关
        </el-button>
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
              <span class="card-title">报关模板说明</span>
            </div>
          </template>
          <div class="ref-table">
            <div class="ref-row ref-header">
              <span>Sheet</span>
              <span>内容</span>
            </div>
            <div class="ref-row">
              <span class="field-code">报关单</span>
              <span class="field-desc">中华人民共和国海关出口货物报关单</span>
            </div>
            <div class="ref-row">
              <span class="field-code">发票</span>
              <span class="field-desc">商业发票 Commercial Invoice</span>
            </div>
            <div class="ref-row">
              <span class="field-code">箱单</span>
              <span class="field-desc">装箱单 Packing List</span>
            </div>
            <div class="ref-row">
              <span class="field-code">合同</span>
              <span class="field-desc">销售合同 Sales Contract</span>
            </div>
            <div class="ref-row">
              <span class="field-code">委托书</span>
              <span class="field-desc">报关委托书 Power of Attorney</span>
            </div>
          </div>
        </el-card>
      </aside>

      <!-- Right: Document Editor -->
      <main class="editor-panel">
        <el-card class="editor-card" body-style="padding: 0;">
          <DocumentEditor
            v-if="currentDocKey"
            :key="currentDocKey"
            :document-server-url="currentConfig.documentServerUrl"
            :doc-key="currentDocKey"
            :token="currentConfig.token"
            :download-url="currentConfig.downloadUrl"
            :url="currentConfig.url"
            :doc-type="currentConfig.docType"
          />
          <div v-else class="editor-empty">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#bfbfbf" stroke-width="1.2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            <p>请从上方选择订单并点击「报关」生成报关资料</p>
          </div>
        </el-card>
      </main>
    </div>

    <MyDocumentsDrawer v-model="showMyDocuments" @open-doc="onOpenMyDoc" />

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import DocumentEditor from '@/views/phase2/components/DocumentEditor.vue'
import MyDocumentsDrawer from '@/views/phase2/components/MyDocumentsDrawer.vue'
import { phase2Api } from '@/api/phase2'
import { getOrderComparison, getOrderPiContracts } from '@/api/merge'
import { getDashboardOrders, type DashboardOrder } from '@/api/dashboard'

const route = useRoute()

const selectedOrderId = ref<number | null>(null)
const orderList = ref<DashboardOrder[]>([])
const currentOrderItems = ref<any[]>([])
const currentDocKey = ref('')
const currentConfig = ref<any>({})
const showMyDocuments = ref(false)

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
  const data = await getDashboardOrders({ page_size: 100 })
  orderList.value = data.orders || []
}

async function onOrderChange(orderId: number) {
  if (!orderId) return
  try {
    const data = await getOrderComparison(orderId)
    currentOrderItems.value = data.items || []
    const pis = await getOrderPiContracts(orderId)
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
    // ignore
  }
}

async function openCustoms() {
  if (!selectedOrderId.value) return
  try {
    const res = await phase2Api.generateCustoms(selectedOrderId.value)
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('报关资料生成失败: ' + (e.message || ''))
  }
}

async function onOpenMyDoc(doc: any) {
  showMyDocuments.value = false
  currentDocKey.value = doc.doc_key
  try {
    const fileType = doc.docType || 'xlsx'
    const res = await phase2Api.getJwt(doc.doc_key, fileType)
    currentConfig.value = {
      ...res.data,
      url: doc.url,
      downloadUrl: doc.downloadUrl,
    }
  } catch (e: any) {
    ElMessage.error('文档加载失败: ' + (e.message || ''))
  }
}

onMounted(() => {
  loadOrderList()
  if (selectedOrderId.value) onOrderChange(selectedOrderId.value)
})
</script>

<style scoped>
/* ── Root ─────────────────────────────────────── */
.phase3 {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  min-height: 100vh;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

/* ── Toolbar ─────────────────────────────────── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 56px;
  padding: 0 20px;
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
  border-radius: 12px;
}
:deep(.el-card__header) {
  padding: 10px 14px;
  border-bottom: 1px solid var(--el-border-color-light, #e4e7ed);
}
:deep(.el-card__body) {
  padding: 12px 14px;
}
.card-header {
  font-weight: 600;
  font-size: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
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
  grid-template-columns: 80px 1fr;
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
}

.editor-card {
  border-radius: 12px;
  overflow: hidden;
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
}
.editor-card :deep(.el-card__body) {
  flex: 1;
  height: 0;
  padding: 0;
}

.editor-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 180px);
  gap: 12px;
  color: #bfbfbf;
}
.editor-empty p {
  font-size: 14px;
  color: #bfbfbf;
  margin: 0;
}

/* ── Scrollbar ──────────────────────────────── */
.info-panel::-webkit-scrollbar { width: 4px; }
.info-panel::-webkit-scrollbar-track { background: transparent; }
.info-panel::-webkit-scrollbar-thumb { background: #dcdfe6; border-radius: 2px; }
</style>