<template>
  <div class="phase2">

    <!-- ── Page Header ─────────────────────────────── -->
    <div class="page-header">
      <h1 class="page-title">单证生成工作流</h1>
      <div class="page-header-row">
        <div class="header-select">
          <label class="header-select-label">订单</label>
          <el-select
            v-model="selectedOrderId"
            placeholder="选择订单"
            size="small"
            class="header-select-input"
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
        <div class="header-actions">
          <el-button
            type="primary"
            size="small"
            :disabled="!selectedOrderId && !selectedLedgerId"
            v-track="{ event: 'generate_document', module: 'phase2', detail: { doc_type: 'booking' } }"
            @click="showBookingDialog = true"
          >
            订舱单
          </el-button>
          <el-button
            type="primary"
            size="small"
            :disabled="!selectedOrderId && !selectedLedgerId"
            v-track="{ event: 'generate_document', module: 'phase2', detail: { doc_type: 'loi' } }"
            @click="openDocument('loi')"
          >
            LOI保函
          </el-button>
          <el-button
            size="small"
            v-track="{ event: 'generate_document', module: 'phase2', detail: { doc_type: 'msds' } }"
            @click="showMsdsDialog = true"
          >
            MSDS
          </el-button>
          <el-button
            size="small"
            :disabled="!selectedLedgerId"
            v-track="{ event: 'generate_document', module: 'phase2', detail: { doc_type: 'customs' } }"
            @click="openCustomsDocument"
          >
            报关资料
          </el-button>
          <el-dropdown @command="(cmd: 'booking' | 'loi' | 'msds') => openBlankTemplate(cmd)" trigger="click">
            <el-button size="small">
              空白模板
              <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="booking">订舱单 Booking</el-dropdown-item>
                <el-dropdown-item command="loi">LOI保函</el-dropdown-item>
                <el-dropdown-item command="msds">MSDS物质安全表</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button size="small" @click="showMyDocuments = true">我的模板</el-button>
        </div>
      </div>
    </div>

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
              <div v-if="(selectedOrderId || selectedLedgerId) && shipperEditing" class="shipper-edit-row">
                <el-input
                  v-model="currentOrderInfo.shipper"
                  type="textarea"
                  :autosize="{ minRows: 2 }"
                  size="small"
                  placeholder="公司名称+地址+TEL/传真"
                />
              </div>
              <!-- 选择状态 -->
              <el-select
                v-else-if="selectedOrderId || selectedLedgerId"
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
              <el-input v-if="selectedOrderId || selectedLedgerId" v-model="currentOrderInfo.consignee" type="textarea" :autosize="{ minRows: 2 }" size="small" placeholder="公司名称+地址+TEL/传真" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">通知人</span>
              <el-input v-if="selectedOrderId || selectedLedgerId" v-model="currentOrderInfo.notify" type="textarea" :autosize="{ minRows: 2 }" size="small" placeholder="公司名称+地址+TEL/传真" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div class="info-row">
              <span class="info-label">卸货港</span>
              <el-input v-if="selectedOrderId || selectedLedgerId" v-model="currentOrderInfo.port" size="small" placeholder="可编辑" />
              <span v-else class="info-value muted">—</span>
            </div>
            <div v-if="currentOrderItems.length >= 1" class="product-list-section" style="margin-top: 8px;">
              <el-table :data="currentOrderItems" size="small" border fit>
                <el-table-column prop="customs_name" label="报关名称" min-width="80" show-overflow-tooltip />
                <el-table-column prop="product_en" label="英文" min-width="70" show-overflow-tooltip />
                <el-table-column prop="order.hs_code" label="HS Code" min-width="60" />
                <el-table-column prop="appearance" label="外观" min-width="70" show-overflow-tooltip />
                <el-table-column prop="customs_ingredients" label="成分" min-width="80" show-overflow-tooltip />
              </el-table>
            </div>
            <div class="info-row">
              <span class="info-label">净重</span>
              <el-input v-if="selectedOrderId || selectedLedgerId" v-model="currentOrderInfo.net_weight_kg" size="small" placeholder="可编辑">
                <template #append>kg</template>
              </el-input>
              <span v-else class="info-value muted">— kg</span>
            </div>
            <div class="info-row">
              <span class="info-label">毛重</span>
              <el-input v-if="selectedOrderId || selectedLedgerId" v-model="currentOrderInfo.gross_weight_kg" size="small" placeholder="可编辑">
                <template #append>kg</template>
              </el-input>
              <span v-else class="info-value muted">— kg</span>
            </div>
            <div class="info-row">
              <span class="info-label">体积</span>
              <el-input v-if="selectedOrderId || selectedLedgerId" v-model="currentOrderInfo.volume_cbm" size="small" placeholder="可编辑">
                <template #append>m³</template>
              </el-input>
              <span v-else class="info-value muted">— m³</span>
            </div>
            <div class="info-row">
              <span class="info-label">桶数/托盘数</span>
              <el-input v-if="selectedOrderId || selectedLedgerId" v-model="currentOrderInfo.drum_count" size="small" placeholder="可编辑" />
              <span v-else class="info-value muted">—</span>
            </div>

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
    <MSDSGeneratorDialog v-model="showMsdsDialog" :order-items="currentOrderItems" @generated="onMsdsGenerated" />

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
import { ArrowDown } from '@element-plus/icons-vue'
import { phase2Api } from '@/api/phase2'
import { getOrderList, getOrderComparison, getOrderPiContracts, type OrderListItem } from '@/api/merge'
import { getDashboardOrders, type DashboardOrder } from '@/api/dashboard'
import { ordersApi } from '@/api/orders'
import { nameMappingApi } from '@/api/name_mapping'
import { SHIPPER_OPTIONS } from '@/constants/shippers'

const SHIPPER_MAP: Record<string, string> = {
  '宏昊': SHIPPER_OPTIONS[0],
  '宏昊化工': SHIPPER_OPTIONS[0],
  '广东宏昊': SHIPPER_OPTIONS[0],
  '广东宏昊化工': SHIPPER_OPTIONS[0],
}

function getShipperFromTitle(title?: string | null): string {
  if (!title) return SHIPPER_OPTIONS[0]
  const t = title.trim()
  if (SHIPPER_MAP[t]) return SHIPPER_MAP[t]
  for (const [key, val] of Object.entries(SHIPPER_MAP)) {
    if (key.includes(t) || t.includes(key)) return val
  }
  return SHIPPER_OPTIONS[0]
}

const route = useRoute()

const selectedOrderId = ref<number | null>(null)
const selectedLedgerId = ref<number | null>(null)
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
  consignee_name: '',
  consignee_address: '',
  consignee_tel: '',
  shipment_title: '',
  notify: 'SAME AS CONSIGNEE',
  port: '',
  product_cn: '',
  product_en: '',
  hs_code: '',
  net_weight_kg: '',
  gross_weight_kg: '',
  volume_cbm: '',
  drum_count: '',
  pallet_count: '',
})

if (route.query.orderId) {
  selectedOrderId.value = Number(route.query.orderId)
}
if (route.query.ledgerId) {
  selectedLedgerId.value = Number(route.query.ledgerId)
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

  // 先找到订单号
  const orderItem = orderList.value.find(o => o.order_id === orderId)
  const orderNo = orderItem?.order_no || ''

  // 优先从台账加载（数据更完整）
  if (orderNo) {
    const ledgerRecord = await ordersApi.getLedgerRecordByOrderNo(orderNo)
    if (ledgerRecord) {
      // 用 loadLedgerRecord 相同的逻辑填充数据
      const items = ledgerRecord.items || []

      const totalNw = items.reduce((sum: number, it: any) => sum + (it.net_weight_kg || 0), 0)
      const totalGw = items.reduce((sum: number, it: any) => sum + (it.gross_weight_kg || 0), 0)
      const totalVol = items.reduce((sum: number, it: any) => sum + (it.volume_cbm || 0), 0)
      const totalDrums = items.reduce((sum: number, it: any) => sum + (it.drum_count || 0), 0)
      const totalPallets = items.reduce((sum: number, it: any) => sum + (it.pallet_count || 0), 0)

      const customsNameAll = items.map((it: any) => it.customs_name).filter(Boolean).join(' / ')
      const hsCodeAll = items.map((it: any) => it.hs_code).filter(Boolean).join(' / ')

      const mappedItems = items.map((it: any) => ({
        internal_code: it.internal_code,
        customs_name: it.customs_name,
        product_en: it.product_en || '',
        customs_ingredients: it.customs_ingredients || '',
        appearance: it.product_appearance || '',
        order: {
          hs_code: it.hs_code,
          quantity: it.quantity_kg,
          gross_weight: it.gross_weight_kg,
          volume: it.volume_cbm,
        },
      }))
      currentOrderItems.value = mappedItems

      for (const item of currentOrderItems.value) {
        const cn = item.customs_name || ''
        if (cn && !item.product_en) {
          try {
            const res = await nameMappingApi.lookupByCn(cn)
            if (res.data.en) item.product_en = res.data.en
          } catch { /* ignore */ }
        }
      }

      let productEn = ''
      const firstCustomsName = items[0]?.customs_name || ''
      if (firstCustomsName) {
        try {
          const res = await nameMappingApi.lookupByCn(firstCustomsName)
          productEn = res.data.en || ''
        } catch { /* ignore */ }
      }
      const productEnAll = items.map((it: any) => it.product_en).filter(Boolean).join(' / ')

      const consigneeFull = [ledgerRecord.consignee_name, ledgerRecord.consignee_address].filter(Boolean).join('\n')

      currentOrderInfo.value = {
        order_no: ledgerRecord.order_no || '',
        customer_code: ledgerRecord.customer_code || '',
        shipper: getShipperFromTitle(ledgerRecord.shipment_title),
        consignee: consigneeFull,
        consignee_name: ledgerRecord.consignee_name || '',
        consignee_address: ledgerRecord.consignee_address || '',
        consignee_tel: ledgerRecord.consignee_tel || '',
        shipment_title: ledgerRecord.shipment_title || '',
        notify: 'SAME AS CONSIGNEE',
        port: ledgerRecord.destination || '',
        product_cn: customsNameAll,
        product_en: productEnAll || productEn,
        hs_code: hsCodeAll,
        net_weight_kg: totalNw ? String(Math.round(totalNw * 10) / 10) : '',
        gross_weight_kg: totalGw ? String(Math.round(totalGw * 10) / 10) : '',
        volume_cbm: totalVol ? String(Math.round(totalVol * 1000) / 1000) : '',
        drum_count: totalDrums ? String(totalDrums) : '',
        pallet_count: totalPallets ? String(totalPallets) : (items[0]?.pallet_count != null ? String(items[0].pallet_count) : ''),
      }
      selectedPiNo.value = ledgerRecord.pi_no || ledgerRecord.order_no || ''
      selectedLedgerId.value = ledgerRecord.id

      const shipperVal = getShipperFromTitle(ledgerRecord.shipment_title)
      currentOrderInfo.value.shipper = shipperVal
      shipperSelectValue.value = shipperVal === SHIPPER_OPTIONS[0] ? 'HONGHAO' : (shipperVal ? '__other__' : '')

      if (ledgerRecord.pi_no) {
        piList.value = [{ pi_no: ledgerRecord.pi_no, consignee_name: ledgerRecord.consignee_name || '', consignee_address: ledgerRecord.consignee_address || '', destination: ledgerRecord.destination || '' }]
      }
      return
    }
  }

  // 台账无记录，走原来的 comparison 逻辑
  try {
    const data = await getOrderComparison(orderId)
    const enrichedItems = (data.items || []).map((it: any) => ({
      ...it,
      product_en: it.order?.product_en || '',
      customs_ingredients: it.order?.customs_ingredients || '',
      appearance: it.order?.appearance || '',
    }))
    currentOrderItems.value = enrichedItems

    for (const item of currentOrderItems.value) {
      const cn = item.customs_name || item.order?.customs_name || ''
      if (cn && !item.product_en) {
        try {
          const res = await nameMappingApi.lookupByCn(cn)
          if (res.data.en) item.product_en = res.data.en
        } catch { /* ignore */ }
      }
    }
    if (data.pi_no) selectedPiNo.value = data.pi_no
    const pis = await getOrderPiContracts(orderId)
    piList.value = pis
    if (pis.length > 0 && !selectedPiNo.value) {
      selectedPiNo.value = pis[0].pi_no
    }
    const items = data.items || []
    const firstCustomsName = items[0]?.order?.customs_name || items[0]?.pi?.customs_name || ''
    let productEn = ''
    if (firstCustomsName) {
      try {
        const res = await nameMappingApi.lookupByCn(firstCustomsName)
        productEn = res.data.en || ''
      } catch {
        productEn = ''
      }
    }
    const customsNameAll = items.map(it => it.order?.customs_name || it.pi?.customs_name).filter(Boolean).join(' / ')
    const hsCodeAll = items.map(it => it.order?.hs_code).filter(Boolean).join(' / ')
    const productEnAll = items.map(it => (it as any).product_en).filter(Boolean).join(' / ')
    const piConsigneeName = (pis[0] as any)?.consignee_name || ''
    const piConsigneeAddr = (pis[0] as any)?.consignee_address || ''
    const consigneeFull = [piConsigneeName, piConsigneeAddr].filter(Boolean).join('\n')
    currentOrderInfo.value = {
      order_no: data.order_no || '',
      customer_code: data.customer_code || '',
      shipper: '',
      consignee: consigneeFull,
      consignee_name: piConsigneeName,
      consignee_address: piConsigneeAddr,
      consignee_tel: (pis[0] as any)?.consignee_tel || '',
      shipment_title: '',
      notify: 'SAME AS CONSIGNEE',
      port: (pis[0] as any)?.destination || '',
      product_cn: customsNameAll,
      product_en: productEnAll || productEn,
      hs_code: hsCodeAll,
      net_weight_kg: data.net_weight_kg ? String(data.net_weight_kg) : '',
      gross_weight_kg: data.gross_weight_kg ? String(data.gross_weight_kg) : '',
      volume_cbm: data.volume_cbm ? String(data.volume_cbm) : '',
      drum_count: data.drum_count ? String(data.drum_count) : '',
      pallet_count: data.pallet_count ? String(data.pallet_count) : '',
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
    ElMessage.error('文档生成失败，请稍后重试')
  }
}

async function openCustomsDocument() {
  if (!selectedLedgerId.value) {
    ElMessage.warning('请先从台账列表选择一条记录')
    return
  }
  try {
    const res = await phase2Api.generateCustoms(null, selectedLedgerId.value)
    currentDocKey.value = res.data.documentKey || res.data.docKey || ''
    currentConfig.value = res.data || res
  } catch (e: any) {
    ElMessage.error('报关资料生成失败，请稍后重试')
  }
}

const bookingInitialValues = computed(() => {
  const items = currentOrderItems.value || []
  return {
    shipper: currentOrderInfo.value.shipper,
    consignee: currentOrderInfo.value.consignee,
    consignee_name: currentOrderInfo.value.consignee_name,
    consignee_address: currentOrderInfo.value.consignee_address,
    consignee_tel: currentOrderInfo.value.consignee_tel,
    shipment_title: currentOrderInfo.value.shipment_title,
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
    ElMessage.error('订舱单生成失败，请稍后重试')
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
    ElMessage.error('模板打开失败，请稍后重试')
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
    ElMessage.error('文档加载失败，请稍后重试')
  }
}

onMounted(() => {
  loadOrderList()
  if (selectedOrderId.value) onOrderChange(selectedOrderId.value)
  if (selectedLedgerId.value) loadLedgerRecord(selectedLedgerId.value)
})

async function loadLedgerRecord(ledgerId: number) {
  try {
    const record = await ordersApi.getLedgerRecord(ledgerId)
    if (!record) return
    const items = record.items || []

    // 汇总多产品的包装数据
    const totalNw = items.reduce((sum: number, it: any) => sum + (it.net_weight_kg || 0), 0)
    const totalGw = items.reduce((sum: number, it: any) => sum + (it.gross_weight_kg || 0), 0)
    const totalVol = items.reduce((sum: number, it: any) => sum + (it.volume_cbm || 0), 0)
    const totalDrums = items.reduce((sum: number, it: any) => sum + (it.drum_count || 0), 0)
    const totalPallets = items.reduce((sum: number, it: any) => sum + (it.pallet_count || 0), 0)

    // 多产品报关名称/HS Code 用 / 拼接（使用报关名称而非产品中文名）
    const customsNameAll = items.map((it: any) => it.customs_name).filter(Boolean).join(' / ')
    const hsCodeAll = items.map((it: any) => it.hs_code).filter(Boolean).join(' / ')
    // 收货人 = 名称 + 地址（与 onOrderChange 保持一致）
    const consigneeFull = [record.consignee_name, record.consignee_address].filter(Boolean).join('\n')

    // 构造与 onOrderChange 相同结构的 items（表格列引用 order.hs_code 等嵌套字段）
    const mappedItems = items.map((it: any) => ({
      internal_code: it.internal_code,
      customs_name: it.customs_name,
      product_en: it.product_en || '',
      customs_ingredients: it.customs_ingredients || '',
      appearance: it.product_appearance || '',
      order: {
        hs_code: it.hs_code,
        quantity: it.quantity_kg,
        gross_weight: it.gross_weight_kg,
        volume: it.volume_cbm,
      },
    }))
    currentOrderItems.value = mappedItems
    
    // Look up English names
    for (const item of currentOrderItems.value) {
      const cn = item.customs_name || ''
      if (cn && !item.product_en) {
        try {
          const res = await nameMappingApi.lookupByCn(cn)
          if (res.data.en) item.product_en = res.data.en
        } catch { /* ignore */ }
      }
    }

    // 查询英文名（取第一个报关名称做映射）
    let productEn = ''
    const firstCustomsName = items[0]?.customs_name || ''
    if (firstCustomsName) {
      try {
        const res = await nameMappingApi.lookupByCn(firstCustomsName)
        productEn = res.data.en || ''
      } catch { /* ignore */ }
    }
    const productEnAll = items.map((it: any) => it.product_en).filter(Boolean).join(' / ')

    // 填充 currentOrderInfo（使用报关名称）
    currentOrderInfo.value = {
      order_no: record.order_no || '',
      customer_code: record.customer_code || '',
      shipper: getShipperFromTitle(record.shipment_title),
      consignee: consigneeFull,
      consignee_name: record.consignee_name || '',
      consignee_address: record.consignee_address || '',
      consignee_tel: record.consignee_tel || '',
      shipment_title: record.shipment_title || '',
      notify: 'SAME AS CONSIGNEE',
      port: record.destination || '',
      product_cn: customsNameAll,
      product_en: productEnAll || productEn,
      hs_code: hsCodeAll,
      net_weight_kg: totalNw ? String(Math.round(totalNw * 10) / 10) : '',
      gross_weight_kg: totalGw ? String(Math.round(totalGw * 10) / 10) : '',
      volume_cbm: totalVol ? String(Math.round(totalVol * 1000) / 1000) : '',
      drum_count: totalDrums ? String(totalDrums) : '',
      pallet_count: totalPallets ? String(totalPallets) : (items[0]?.pallet_count != null ? String(items[0].pallet_count) : ''),
    }
    selectedPiNo.value = record.pi_no || record.order_no || ''
    // 设置 selectedOrderId 使顶部按钮可操作
    selectedOrderId.value = record.id
    // 同步发货人下拉框选中值
    const shipperVal = getShipperFromTitle(record.shipment_title)
    currentOrderInfo.value.shipper = shipperVal
    shipperSelectValue.value = shipperVal === SHIPPER_OPTIONS[0] ? 'HONGHAO' : (shipperVal ? '__other__' : '')
    // 填充 PI 下拉列表
    if (record.pi_no) {
      piList.value = [{ pi_no: record.pi_no, consignee_name: record.consignee_name || '', consignee_address: record.consignee_address || '', destination: record.destination || '' }]
    }
  } catch (e: any) {
    ElMessage.error('加载台账记录失败，请稍后重试')
  }
}
</script>

<style scoped>
/* ── Root ─────────────────────────────────────── */
.phase2 {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ── Page Header (matches Phase 1) ──────────────── */
.page-header { margin-bottom: 20px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-header-row { display: flex; align-items: center; justify-content: space-between; }
.header-select {
  display: flex;
  align-items: center;
  gap: 8px;
}
.header-select-label {
  font-size: 14px;
  color: var(--el-text-color-secondary, #909399);
  white-space: nowrap;
}
.header-select-input { width: 240px; }
.header-actions { display: flex; gap: 8px; }

/* ── Main Layout ─────────────────────────── */
.main-layout {
  display: flex;
  gap: 0;
  align-items: stretch;
  height: calc(100vh - 180px);
  overflow: hidden;
}
.info-panel {
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
}
.info-panel > .info-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.info-panel > .info-card > :deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
}
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
  height: 100%;
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
  height: 100%;
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
  flex: 1;
}
</style>
