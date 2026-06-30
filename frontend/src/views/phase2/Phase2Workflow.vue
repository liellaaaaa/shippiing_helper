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
              :key="o.order_id"
              :label="o.order_no + ' · ' + o.customer_code"
              :value="o.order_id"
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
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M8 13h8M8 17h8M8 9h2"/>
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
      <aside class="info-panel" :style="{ width: leftWidth + 'px' }">
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
              <!-- 编辑状态 -->
              <div v-if="selectedOrderId && shipperEditing" class="shipper-edit-row">
                <el-input
                  v-model="currentOrderInfo.shipper"
                  type="textarea"
                  :rows="3"
                  size="small"
                  placeholder="公司名称+地址+TEL/传真"
                />
              </div>
              <!-- 选择状态 -->
              <el-select
                v-else-if="selectedOrderId"
                v-model="shipperSelectValue"
                placeholder="请选择发货人"
                size="small"
                style="width:100%"
                @change="(val: string) => { if (val === '__other__') { shipperEditing = true; shipperSelectValue = '' } else if (val === 'HONGHAO') { currentOrderInfo.shipper = SHIPPER_OPTIONS[0] } }"
              >
                <el-option label="HONGHAO CHEMICAL CO., LTD." value="HONGHAO" />
                <el-option label="其他" value="__other__" />
              </el-select>
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">收货人</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.consignee" type="textarea" :rows="2" size="small" placeholder="公司名称+地址+TEL/传真" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">通知人</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.notify" type="textarea" :rows="2" size="small" placeholder="公司名称+地址+TEL/传真" />
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
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.gross_weight_kg" size="small" placeholder="可编辑">
                <template #append>kg</template>
              </el-input>
              <span v-else class="info-value muted">— kg</span>
            </div>
            <div class="info-row">
              <span class="info-label">体积(CBM)</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.volume_cbm" size="small" placeholder="可编辑">
                <template #append>m³</template>
              </el-input>
              <span v-else class="info-value muted">— m³</span>
            </div>
            <div class="info-row">
              <span class="info-label">桶数</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.drum_count" size="small" placeholder="可编辑" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">托盘数</span>
              <el-input v-if="selectedOrderId" v-model="currentOrderInfo.pallet_count" size="small" placeholder="可编辑" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">20GP判断</span>
              <span v-if="selectedOrderId && currentOrderInfo.fits_20gp" class="info-value" :class="currentOrderInfo.fits_20gp === '适合' ? 'text-success' : 'text-danger'">{{ currentOrderInfo.fits_20gp }}</span>
              <span v-else class="info-value muted">—</span>
            </div>
            <!-- 产品明细列表 -->
            <div v-if="currentOrderItems.length >= 1" class="product-list-section">
              <el-collapse>
                <el-collapse-item title="产品明细" name="products">
                  <el-table :data="currentOrderItems" size="small" stripe>
                    <el-table-column prop="internal_code" label="Internal Code" min-width="100" />
                    <el-table-column prop="product_cn" label="品名" min-width="120" show-overflow-tooltip />
                    <el-table-column prop="order.hs_code" label="HS Code" min-width="80" />
                    <el-table-column prop="order.quantity" label="数量(kg)" min-width="80" align="right" />
                    <el-table-column prop="order.gross_weight" label="毛重(kg)" min-width="80" align="right" />
                    <el-table-column prop="order.volume" label="体积(m³)" min-width="80" align="right" />
                  </el-table>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </el-card>

        <!-- Field Reference Card: 运输鉴定报告 -->
        <el-card class="info-card ref-card" shadow="never" style="margin-top: 12px; flex: 1; display: flex; flex-direction: column; overflow: hidden;">
          <template #header>
            <div class="card-header">
              <span class="card-title">字段参考</span>
            </div>
          </template>
          <div style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">
            <FieldReferenceCard
              style="flex: 1; overflow: hidden;"
            />
          </div>
        </el-card>
      </aside>

      <!-- 分隔条 -->
      <div class="resizer" @mousedown="startResize"></div>

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
            :callback-url="currentConfig.callbackUrl"
            :doc-type="currentConfig.docType"
            :title="currentConfig.title"
          />
          <div v-else class="editor-empty">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#bfbfbf" stroke-width="1.2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            <p>请从上方选择订单并生成文档</p>
          </div>
        </el-card>
      </main>
    </div>

    <!-- ── Booking Dialog (核对对话框) ──────────── -->
    <BookingConfirmDialog
      v-model="showBookingDialog"
      :initial-values="bookingInitialValues"
      @confirm="onBookingConfirm"
    />

    <!-- ── MSDS Generator Dialog ──────────────────── -->
    <MSDSGeneratorDialog v-model="showMsdsDialog" @generated="onMsdsGenerated" />

    <MyDocumentsDrawer v-model="showMyDocuments" @open-doc="onOpenMyDoc" />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import DocumentEditor from './components/DocumentEditor.vue'
import BookingConfirmDialog from './components/BookingConfirmDialog.vue'
import MSDSGeneratorDialog from './components/MSDSGeneratorDialog.vue'
import MyDocumentsDrawer from './components/MyDocumentsDrawer.vue'
import FieldReferenceCard from './components/FieldReferenceCard.vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { phase2Api } from '@/api/phase2'
import { getOrderList, getOrderComparison, getOrderPiContracts, type OrderListItem } from '@/api/merge'
import { getDashboardOrders, type DashboardOrder } from '@/api/dashboard'
import { nameMappingApi } from '@/api/name_mapping'
import { SHIPPER_OPTIONS } from '@/constants/shippers'

const route = useRoute()

const selectedOrderId = ref<number | null>(null)
const shipperEditing = ref(false)
const shipperSelectValue = ref('')
const selectedPiNo = ref<string>('')
const orderList = ref<DashboardOrder[]>([])
const piList = ref<any[]>([])
const currentOrderItems = ref<any[]>([])
const currentDocKey = ref('')
const currentConfig = ref<any>({})
const leftWidth = ref(400)
const isResizing = ref(false)

function startResize(e: MouseEvent) {
  isResizing.value = true
  const startX = e.clientX
  const startWidth = leftWidth.value
  const containerEl = document.querySelector('.main-layout') as HTMLElement

  function onMouseMove(ev: MouseEvent) {
    if (!isResizing.value) return
    const dx = ev.clientX - startX
    const containerWidth = containerEl?.offsetWidth || window.innerWidth
    leftWidth.value = Math.min(containerWidth * 0.75, Math.max(containerWidth * 0.15, startWidth + dx))
  }
  function onMouseUp() {
    isResizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}
const showMsdsDialog = ref(false)
const showMyDocuments = ref(false)
const showBookingDialog = ref(false)
const selectedBookingTemplate = ref<'xls' | 'xlsx'>('xlsx')

// Editable order info fields
const currentOrderInfo = ref({
  order_no: '',
  customer_code: '',
  shipper: '',
  consignee: '',
  notify: 'SAME AS CONSIGNEE',
  port: '',
  product_cn: '',
  product_en: '',
  hs_code: '',
  gross_weight_kg: '',
  volume_cbm: '',
  drum_count: '',
  pallet_count: '',
  fits_20gp: '',
})

if (route.query.orderId) {
  selectedOrderId.value = Number(route.query.orderId)
}

async function loadOrderList() {
  const data = await getDashboardOrders({ page_size: 100 })
  orderList.value = data.orders || []
}

function selectShipperPreset(text: string) {
  currentOrderInfo.value.shipper = text
}

async function onOrderChange(orderId: number): Promise<void> {
  selectedPiNo.value = ''
  shipperEditing.value = false
  shipperSelectValue.value = ''
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
    // Populate editable fields — 汇总所有产品的品名/英文名/HS Code
    const items = data.items || []
    // 英文名取第一个产品的（有值的情况下）
    const firstCn = items[0]?.product_cn || ''
    let productEn = ''
    if (firstCn) {
      try {
        const res = await nameMappingApi.lookupByCn(firstCn)
        productEn = res.data.en || ''
      } catch {
        productEn = ''
      }
    }
    // 多产品时用 / 连接
    const productCnAll = items.map(it => it.product_cn).filter(Boolean).join(' / ')
    const hsCodeAll = items.map(it => it.order?.hs_code).filter(Boolean).join(' / ')
    const productEnAll = items.map(it => (it as any).product_en).filter(Boolean).join(' / ')
    // 收货人 = 名称 + 地址（用换行连接）
    const piConsigneeName = (pis[0] as any)?.consignee_name || ''
    const piConsigneeAddr = (pis[0] as any)?.consignee_address || ''
    const consigneeFull = [piConsigneeName, piConsigneeAddr].filter(Boolean).join('\n')
    currentOrderInfo.value = {
      order_no: data.order_no || '',
      customer_code: data.customer_code || '',
      shipper: '',
      consignee: consigneeFull,
      notify: 'SAME AS CONSIGNEE',
      port: (pis[0] as any)?.destination || '',
      product_cn: productCnAll,
      product_en: productEnAll || productEn,
      hs_code: hsCodeAll,
      gross_weight_kg: data.gross_weight_kg ? String(data.gross_weight_kg) : '',
      volume_cbm: data.volume_cbm ? String(data.volume_cbm) : '',
      drum_count: data.drum_count ? String(data.drum_count) : '',
      pallet_count: data.pallet_count ? String(data.pallet_count) : '',
      fits_20gp: data.fits_20gp || '',
    }
  } catch (e) {
    piList.value = []
  }
}

async function openDocument(type: 'booking' | 'loi') {
  if (type === 'booking') return
  try {
    const res = await phase2Api.generateLoi(currentOrderInfo.value.order_no, selectedPiNo.value)
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('文档生成失败: ' + (e.message || ''))
  }
}

const bookingInitialValues = computed(() => {
  const items = currentOrderItems.value || []
  return {
    shipper: currentOrderInfo.value.shipper,
    consignee: currentOrderInfo.value.consignee,
    notify: currentOrderInfo.value.notify,
    port: currentOrderInfo.value.port,
    customs_names: items.map(it => it.customs_name || it.product_cn || ''),
    gross_weight: currentOrderInfo.value.gross_weight_kg,
    measurement: currentOrderInfo.value.volume_cbm,
    drum_count: currentOrderInfo.value.drum_count,
    pallet_count: currentOrderInfo.value.pallet_count,
  }
})

async function onBookingConfirm(fields: import('./components/BookingConfirmDialog.vue').BookingForm) {
  try {
    const res = await phase2Api.generateBooking({
      ...fields,
      template_type: 'xlsx',
    })
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('订舱单生成失败: ' + (e.message || ''))
  }
}

function onMsdsGenerated(config: any) {
  currentDocKey.value = config.documentKey || config.docKey
  currentConfig.value = config
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

async function onOpenMyDoc(doc: any) {
  showMyDocuments.value = false
  currentDocKey.value = doc.doc_key
  // Fetch fresh config from backend so JWT key and documentKey are properly paired.
  // Using the stored doc.token would have a mismatched key since we now use UUID-based keys.
  try {
    const fileType = doc.docType || 'docx'
    const res = await phase2Api.getJwt(doc.doc_key, fileType)
    currentConfig.value = {
      ...res.data,
      url: doc.url,        // OnlyOffice Document Server URL (host.docker.internal)
      downloadUrl: doc.downloadUrl,  // browser-accessible download URL
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
.phase2 {
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
.main-layout { display: flex; gap: 0; align-items: stretch; overflow: hidden; }
.info-panel { width: 200px; flex-shrink: 0; display: flex; flex-direction: column; min-width: 0; }
.editor-panel { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }

.resizer {
  width: 6px;
  background: var(--el-border-color-extra-light);
  cursor: col-resize;
  flex-shrink: 0;
  transition: background 0.15s;
  margin: 0 8px;
}
.resizer:hover { background: var(--el-color-primary); }

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
.ref-card :deep(.el-card__body) {
  padding: 0;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
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

.product-list-section {
  margin-top: 8px;
}
.product-list-section :deep(.el-collapse) {
  border: none;
}
.product-list-section :deep(.el-collapse-item__header) {
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
  padding-left: 4px;
  line-height: 28px;
  height: 28px;
}
.product-list-section :deep(.el-collapse-item__wrap) {
  border: none;
}
.product-list-section :deep(.el-collapse-item__content) {
  padding: 0;
}
.product-list-section :deep(.el-table) {
  font-size: 11px;
}


/* ── Editor Panel (Right) ───────────────────── */
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
.msds-search-row {
  margin-bottom: 12px;
}
.msds-file-list {
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color-light, #e4e7ed);
  border-radius: 6px;
}
.msds-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 80px;
  color: var(--el-text-color-placeholder, #c0c4cc);
  font-size: 13px;
}
.msds-file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-extra-light, #f2f6fc);
  transition: background 0.12s;
}
.msds-file-item:last-child { border-bottom: none; }
.msds-file-item:hover { background: var(--el-fill-color-light, #f5f7fa); }
.msds-file-item.selected { background: var(--el-color-primary-light-9, #ecf5ff); }
.msds-file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.msds-file-name {
  font-size: 13px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--el-text-color-primary, #303133);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msds-file-product {
  font-size: 11px;
  color: var(--el-text-color-secondary, #909399);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.msds-file-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
.msds-file-badge.docx { background: #409eff22; color: #409eff; }
.msds-file-badge.doc { background: #e6a23c22; color: #e6a23c; }
.msds-file-badge.pdf { background: #f56c6c22; color: #f56c6c; }

/* ── Scrollbar ──────────────────────────────── */
.info-panel::-webkit-scrollbar { width: 4px; }
.info-panel::-webkit-scrollbar-track { background: transparent; }
.info-panel::-webkit-scrollbar-thumb { background: #dcdfe6; border-radius: 2px; }

.shipper-edit-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.shipper-edit-row .el-textarea {
  flex: 1;
}
</style>
