<template>
  <div class="phase1-workflow">
    <div class="page-header">
      <h1 class="page-title">外贸订单处理工作流</h1>
      <div class="page-header-row">
        <span class="page-subtitle">粘贴订单 → 上传 PI → 预览合并数据 → 确认入库</span>
        <div class="header-actions">
          <el-button size="small" @click="handleReset">重置</el-button>
          <el-button
            type="primary"
            size="small"
            :disabled="!canMerge"
            :loading="saving"
            @click="handleConfirmSave"
          >
            确认入库
          </el-button>
          <el-button
            v-if="savedOrderId"
            type="primary"
            size="small"
            @click="$router.push({ path: '/phase2', query: { orderId: savedOrderId } })"
          >
            进入文档编辑 →
          </el-button>
        </div>
      </div>
    </div>

    <div class="workflow-layout">
      <!-- 左侧输入区 -->
      <div class="input-panel" :style="{ width: leftWidth + 'px' }">
        <el-card class="input-card">
          <template #header>
            <div class="card-header">
              <span>订单数据</span>
              <el-tag v-if="orderParsed" type="success" size="small">已解析</el-tag>
            </div>
          </template>
          <PasteTextarea
            v-model="orderText"
            @parse="handleOrderParse"
            @clear="handleOrderClear"
          />
        </el-card>

        <el-card class="input-card" style="margin-top: 16px;">
          <template #header>
            <div class="card-header">
              <span>PI 合同</span>
              <el-tag v-if="piParsed" type="success" size="small">已解析</el-tag>
            </div>
          </template>
          <PiUploadDragger
            v-if="!piParsed"
            @fileSelected="handlePiFileSelected"
          />
          <div v-else class="pi-file-info">
            <el-icon><document /></el-icon>
            <span class="pi-file-name">{{ piFileName }}</span>
            <el-button text size="small" @click="piParsed = false; piFileName = ''">重新上传</el-button>
          </div>
        </el-card>
      </div>

      <!-- 分隔条 -->
      <div class="resizer" @mousedown="startResize"></div>

      <!-- 右侧预览区 -->
      <div class="preview-panel">
        <!-- 订单+产品+PI 合并为一个卡片 -->
        <el-card class="preview-card">
          <template #header>
            <div class="card-header">
              <span>订单预览</span>
              <el-tag v-if="orderParsed && piParsed" type="success" size="small">已完整</el-tag>
              <el-tag v-else-if="orderParsed || piParsed" type="warning" size="small">待完善</el-tag>
            </div>
          </template>

          <!-- 订单信息（折叠显示） -->
          <el-collapse v-model="collapseActiveNames">
            <el-collapse-item name="order">
              <template #title>
                <span>订单信息</span>
                <el-tag v-if="orderParsed" type="success" size="small" style="margin-left:8px">已解析</el-tag>
              </template>
              <div class="order-header-info">
                <div class="info-row">
                  <span class="info-label">订单号</span>
                  <el-input v-model="orderForm.order_no" size="small" class="info-input" placeholder="待录入" />
                </div>
                <div class="info-row">
                  <span class="info-label">客户编码</span>
                  <el-input v-model="orderForm.customer_code" size="small" class="info-input" placeholder="待录入" />
                </div>
              </div>
            </el-collapse-item>

            <!-- 产品明细 -->
            <el-collapse-item name="items">
              <template #title>
                <span>产品明细（共 {{ orderForm.items.length }} 种）</span>
              </template>
              <el-table :data="orderForm.items" border stripe size="small" max-height="250" style="width:100%">
                <el-table-column prop="internal_code" label="内部编码" width="110" />
                <el-table-column prop="product_cn" label="产品中文名" min-width="120" show-overflow-tooltip />
                <el-table-column prop="customs_name" label="报关名称" width="130">
                  <template #default="{ row }">
                    <el-input v-model="row.customs_name" size="small" />
                  </template>
                </el-table-column>
                <el-table-column prop="spec_kg" label="规格(kg)" width="90" align="center" />
                <el-table-column prop="quantity_kg" label="数量" width="110">
                  <template #default="{ row }">
                    <el-input-number v-model="row.quantity_kg" size="small" :min="0" controls-position="right" class="qty-input" />
                  </template>
                </el-table-column>
                <el-table-column prop="hs_code" label="H.S.Code" width="120">
                  <template #default="{ row }">
                    <el-input v-model="row.hs_code" size="small" />
                  </template>
                </el-table-column>
              </el-table>
            </el-collapse-item>

            <!-- PI 合并数据 -->
            <el-collapse-item name="pi">
              <template #title>
                <span>PI 合并数据</span>
                <el-tag v-if="piParsed" type="success" size="small" style="margin-left:8px">已上传</el-tag>
                <el-tag v-else type="info" size="small" style="margin-left:8px">待上传</el-tag>
              </template>
              <div class="pi-merge-info" v-if="piParsed">
                <div class="info-row">
                  <span class="info-label">PI号</span>
                  <el-input v-model="piForm.pi_no" size="small" class="info-input" />
                </div>
                <div class="info-row">
                  <span class="info-label">PI日期</span>
                  <el-input v-model="piForm.pi_date" size="small" class="info-input" />
                </div>
                <div class="info-row">
                  <span class="info-label">客户编码</span>
                  <el-input v-model="piForm.customer_code" size="small" class="info-input" />
                </div>
                <div class="info-row">
                  <span class="info-label">H.S.Code</span>
                  <el-input v-model="piForm.hs_code" size="small" class="info-input" />
                </div>
                <div class="info-row">
                  <span class="info-label">报关品名</span>
                  <el-input v-model="piForm.customs_name" size="small" class="info-input" />
                </div>
                <!-- PI Header 字段（取到了什么数据就展示什么） -->
                <div class="info-row" v-if="piForm.consignee_name">
                  <span class="info-label">收货人</span>
                  <el-input v-model="piForm.consignee_name" size="small" class="info-input" />
                </div>
                <div class="info-row" v-if="piForm.consignee_address">
                  <span class="info-label">收货人地址</span>
                  <el-input v-model="piForm.consignee_address" size="small" class="info-input" />
                </div>
                <div class="info-row" v-if="piForm.destination">
                  <span class="info-label">目的港</span>
                  <el-input v-model="piForm.destination" size="small" class="info-input" />
                </div>
                <div class="info-row" v-if="piForm.price_term">
                  <span class="info-label">价格条款</span>
                  <el-input v-model="piForm.price_term" size="small" class="info-input" />
                </div>
                <div class="info-row" v-if="piForm.loading_port">
                  <span class="info-label">装货港</span>
                  <el-input v-model="piForm.loading_port" size="small" class="info-input" />
                </div>
                <div class="info-row" v-if="piForm.invoice_to">
                  <span class="info-label">发票抬头</span>
                  <el-input v-model="piForm.invoice_to" size="small" class="info-input" />
                </div>
              </div>
              <div v-else class="empty-placeholder">
                <span>请上传 PI 合同文件（.xls/.xlsx/.pdf）</span>
              </div>
            </el-collapse-item>
          </el-collapse>
        </el-card>

        <el-card class="preview-card" style="margin-top: 12px;">
          <template #header>
            <div class="card-header">
              <span>包装计算</span>
            </div>
          </template>
          <PackagingCalculator
            ref="calcRef"
          />
        </el-card>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import PasteTextarea from '@/components/phase1/PasteTextarea.vue'
import PiUploadDragger from '@/components/phase1/PiUploadDragger.vue'
import { ordersApi, type ParsedOrderSchema } from '@/api/orders'
import { uploadPiFile, type PiUploadResponse } from '@/api/pi'
import { saveOrderPiRecord, type PackagingResult } from '@/api/phase1'
import PackagingCalculator from '@/components/phase1/PackagingCalculator.vue'

// State
const orderText = ref('')
const orderParsed = ref(false)
const orderParsedData = ref<ParsedOrderSchema | null>(null)
const piParsed = ref(false)
const piParsedData = ref<PiUploadResponse | null>(null)
const piFileName = ref('')
const saving = ref(false)
const savedOrderId = ref<number | null>(null)
const packagingResult = ref<PackagingResult | null>(null)
const collapseActiveNames = ref<string[]>(['order', 'items', 'pi'])
const calcRef = ref<InstanceType<typeof PackagingCalculator>>()

// 可拖拽分割条
const leftWidth = ref(400)
const isResizing = ref(false)

function startResize(e: MouseEvent) {
  isResizing.value = true
  const startX = e.clientX
  const startWidth = leftWidth.value
  const workflowEl = document.querySelector('.workflow-layout') as HTMLElement

  function onMouseMove(ev: MouseEvent) {
    if (!isResizing.value) return
    const dx = ev.clientX - startX
    const containerWidth = workflowEl?.offsetWidth || window.innerWidth
    const newWidth = startWidth + dx
    const minW = containerWidth * 0.15
    const maxW = containerWidth * 0.75
    leftWidth.value = Math.min(maxW, Math.max(minW, newWidth))
  }
  function onMouseUp() {
    isResizing.value = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// Order Form
const orderForm = ref({
  order_no: '',
  customer_code: '',
  items: [] as Array<{
    internal_code: string
    product_cn: string
    spec_kg: number
    quantity_kg: number
    unit_price: number
    total_amount: number
    hs_code: string
    customs_name: string
    order_requirement: string
  }>,
})

// PI Form
const piForm = ref({
  pi_no: '',
  customer_code: '',
  pi_date: '',
  internal_code: '',
  quantity: 0,
  unit_price: 0,
  total_amount: 0,
  hs_code: '',
  customs_name: '',
  // PI Header 字段（后端已支持展示）
  consignee_name: '',
  consignee_address: '',
  destination: '',
  loading_port: '',
  price_term: '',
  invoice_to: '',
})

// Computed
const canMerge = computed(() => orderParsed.value && orderForm.value.items.length > 0)

function syncCalculatorFromOrder() {
  if (!calcRef.value) return
  calcRef.value.clearRows()
  for (const item of orderForm.value.items) {
    calcRef.value.addRow(item.internal_code || '', item.product_cn || '', item.quantity_kg || 0)
  }
}

// Handlers
async function handleOrderParse(text: string) {
  try {
    const result = await ordersApi.parsePaste(text)
    if (result.orders.length === 0) {
      ElMessage.warning('未解析到订单数据')
      return
    }
    const first = result.orders[0]
    orderParsedData.value = first

    // 解析所有产品（支持一单多品）
    orderForm.value = {
      order_no: first.order_no || '',
      customer_code: first.customer_code || '',
      items: (first.items || []).map((item: any) => ({
        internal_code: item.internal_code || '',
        product_cn: item.product_cn || '',
        spec_kg: item.spec_kg || 0,
        quantity_kg: item.quantity_kg || 0,
        unit_price: item.unit_price || 0,
        total_amount: item.total_amount || 0,
        hs_code: item.hs_code || '',
        customs_name: item.customs_name || '',
        order_requirement: item.order_requirement || '',
      })),
    }
    orderParsed.value = true

    // 更新计算器
    syncCalculatorFromOrder()

    ElMessage.success(`订单解析成功，共 ${orderForm.value.items.length} 个产品`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '解析失败')
  }
}

async function handlePiFileSelected(file: File) {
  piFileName.value = file.name
  try {
    const result = await uploadPiFile(file)
    piParsedData.value = result

    const firstItem = result.items[0] || {}
    piForm.value = {
      pi_no: result.pi_no || '',
      customer_code: result.customer_code || '',
      pi_date: result.pi_date || '',
      internal_code: firstItem.internal_code || '',
      quantity: firstItem.quantity ?? 0,
      unit_price: firstItem.unit_price ?? 0,
      total_amount: firstItem.total_amount ?? 0,
      hs_code: firstItem.hs_code || '',
      customs_name: firstItem.customs_name || '',
      // PI Header 字段
      consignee_name: result.consignee_name || '',
      consignee_address: result.consignee_address || '',
      destination: result.destination || '',
      loading_port: result.loading_port || '',
      price_term: result.price_term || '',
      invoice_to: result.invoice_to || '',
    }
    piParsed.value = true
    ElMessage.success(`PI 文件 "${file.name}" 解析成功`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || 'PI 解析失败')
  }
}

function handleOrderClear() {
  orderParsed.value = false
  orderParsedData.value = null
  orderForm.value = { order_no: '', customer_code: '', items: [] }
  packagingResult.value = null
}

// Confirm Save
async function handleConfirmSave() {
  if (!canMerge.value) {
    ElMessage.warning('请确保订单已解析')
    return
  }

  saving.value = true
  try {
    // 构建多产品 items 数组
    const items = orderForm.value.items.map(item => ({
      internal_code: item.internal_code,
      product_cn: item.product_cn,
      spec_kg: item.spec_kg,
      quantity_kg: item.quantity_kg,
      unit_price: item.unit_price,
      total_amount: item.total_amount,
      hs_code: item.hs_code,
      customs_name: item.customs_name,
      order_requirement: item.order_requirement,
    }))

    const orderData = {
      order_no: orderForm.value.order_no,
      customer_code: orderForm.value.customer_code,
      items,
    }

    const piData = piParsed.value ? {
      pi_no: piForm.value.pi_no,
      customer_code: piForm.value.customer_code,
      pi_date: piForm.value.pi_date,
      internal_code: piForm.value.internal_code,
      quantity: piForm.value.quantity,
      unit_price: piForm.value.unit_price,
      total_amount: piForm.value.total_amount,
      hs_code: piForm.value.hs_code,
      customs_name: piForm.value.customs_name,
    } : undefined

    // 从计算器获取汇总，并转换为 PackagingResult 格式
    const summary = calcRef.value?.getSummary()
    const packaging_result = summary ? {
      packaging_type: '混合包装',
      drums: summary.total_drums,
      pallets: summary.total_pallets,
      drums_per_pallet: 0,
      net_weight_kg: 0,
      gross_weight_kg: summary.total_weight_kg,
      volume_cbm: summary.total_cbm,
      fits_20gp: summary.fits_20gp ? '适合' : '超出',
      no_pallet: false,
    } : undefined

    // 获取每产品各自的包装计算结果
    const packaging_items = calcRef.value?.getRows() || []

    const resp = await saveOrderPiRecord({
      order_data: orderData,
      pi_data: piData,
      packaging_result,
      packaging_items,
    })

    savedOrderId.value = resp.record_id
    ElMessage.success('数据已成功落库！')
    handleReset()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '落库失败')
  } finally {
    saving.value = false
  }
}

function handleReset() {
  orderText.value = ''
  orderParsed.value = false
  orderParsedData.value = null
  piParsed.value = false
  piParsedData.value = null
  piFileName.value = ''
  packagingResult.value = null
  orderForm.value = { order_no: '', customer_code: '', items: [] }
  piForm.value = { pi_no: '', customer_code: '', pi_date: '', internal_code: '', quantity: 0, unit_price: 0, total_amount: 0, hs_code: '', customs_name: '', consignee_name: '', consignee_address: '', destination: '', loading_port: '', price_term: '', invoice_to: '' }
}
</script>

<style scoped>
.phase1-workflow { padding: 24px; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-header-row { display: flex; align-items: center; justify-content: space-between; }
.page-subtitle { font-size: 14px; color: #909399; margin: 0; }
.header-actions { display: flex; gap: 8px; }

.workflow-layout { display: flex; gap: 0; align-items: stretch; overflow: hidden; }
.input-panel { width: 200px; flex-shrink: 0; display: flex; flex-direction: column; min-width: 0; }
.preview-panel { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }

.resizer {
  width: 6px;
  background: var(--el-border-color-extra-light);
  cursor: col-resize;
  flex-shrink: 0;
  transition: background 0.15s;
  margin: 0 8px;
}
.resizer:hover { background: var(--el-color-primary); }

.input-card, .preview-card { border-radius: 12px; }
.card-header { font-weight: 600; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }

.pkg-placeholder { text-align: center; color: #909399; padding: 20px; }
.pkg-result { padding: 4px 0; }
.packing-scheme { margin-top: 12px; padding: 10px; background: #f5f7fa; border-radius: 6px; font-size: 13px; color: #606266; }

.action-bar { position: sticky; bottom: 0; display: flex; justify-content: flex-end; gap: 12px; padding: 16px 24px; background: white; border-top: 1px solid #e8e8e8; margin-top: 20px; box-shadow: 0 -2px 12px rgba(0,0,0,0.05); }

.pi-file-info { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: #f0f9eb; border-radius: 8px; color: #67c23a; }
.pi-file-name { flex: 1; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Order header info */
.order-header-info { display: flex; flex-direction: column; gap: 8px; }
.info-row { display: flex; align-items: center; gap: 12px; }
.info-label { width: 80px; font-size: 13px; color: #606266; }
.info-input { flex: 1; }

/* Product table inputs */
.qty-input, .price-input { width: 100%; }

/* PI merge info */
.pi-merge-info { display: flex; flex-direction: column; gap: 8px; }

/* Empty state placeholder */
.empty-placeholder {
  text-align: center;
  padding: 12px;
  color: #c0c4cc;
  font-size: 13px;
}

/* Product item rows */
.product-item-card {
  border: 1px solid var(--el-border-color-extra-light);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 8px;
  background: var(--el-fill-color-light);
}
.product-item-header {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
}
.product-item-fields {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.product-item-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.product-item-field label {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}
</style>