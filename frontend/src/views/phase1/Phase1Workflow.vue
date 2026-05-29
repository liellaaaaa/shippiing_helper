<template>
  <div class="phase1-workflow">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">外贸订单处理工作流</h1>
      <p class="page-subtitle">粘贴订单 → 上传 PI → 预览合并数据 → 确认入库</p>
    </div>

    <div class="workflow-layout">
      <!-- 左侧输入区 -->
      <div class="input-panel">
        <!-- 订单输入 -->
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

          <!-- 订单预览（可编辑） -->
          <div v-if="orderParsed" class="order-preview">
            <el-divider content-position="left">订单预览</el-divider>
            <el-form label-width="100px" size="small">
              <el-form-item label="订单号">
                <el-input v-model="orderForm.order_no" />
              </el-form-item>
              <el-form-item label="客户编码">
                <el-input v-model="orderForm.customer_code" />
              </el-form-item>
              <el-form-item label="内部编码">
                <el-input v-model="orderForm.internal_code" />
              </el-form-item>
              <el-form-item label="产品名称">
                <el-input v-model="orderForm.product_cn" />
              </el-form-item>
              <el-form-item label="规格kg">
                <el-input-number v-model="orderForm.spec_kg" :min="0" />
              </el-form-item>
              <el-form-item label="订单量kg">
                <el-input-number v-model="orderForm.quantity_kg" :min="0" />
              </el-form-item>
              <el-form-item label="订单要求">
                <el-input
                  v-model="orderForm.order_requirement"
                  type="textarea"
                  :rows="3"
                  placeholder="包含包装、标签、卡板、出货日期等要求"
                />
              </el-form-item>
            </el-form>
          </div>
        </el-card>

        <!-- PI 上传 -->
        <el-card class="input-card" style="margin-top: 16px;">
          <template #header>
            <div class="card-header">
              <span>PI 合同</span>
              <el-tag v-if="piParsed" type="success" size="small">已解析</el-tag>
            </div>
          </template>

          <PiUploadDragger @fileSelected="handlePiFileSelected" />

          <!-- PI 预览 -->
          <div v-if="piParsed" class="pi-preview">
            <el-divider content-position="left">PI 预览</el-divider>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="PI号">{{ piForm.pi_no }}</el-descriptions-item>
              <el-descriptions-item label="客户编码">{{ piForm.customer_code }}</el-descriptions-item>
              <el-descriptions-item label="日期">{{ piForm.pi_date }}</el-descriptions-item>
              <el-descriptions-item label="数量">{{ piForm.quantity }}</el-descriptions-item>
              <el-descriptions-item label="单价">{{ piForm.unit_price }}</el-descriptions-item>
              <el-descriptions-item label="金额">{{ piForm.total_amount }}</el-descriptions-item>
              <el-descriptions-item label="报关品名">{{ piForm.customs_name }}</el-descriptions-item>
              <el-descriptions-item label="H.S.Code">{{ piForm.hs_code }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </div>

      <!-- 右侧预览区 -->
      <div class="preview-panel">
        <!-- 合并预览表 -->
        <el-card class="preview-card">
          <template #header>
            <div class="card-header">
              <span>合并预览</span>
              <el-tag v-if="canMerge" type="warning" size="small">待确认</el-tag>
              <el-tag v-else type="info" size="small">等待数据</el-tag>
            </div>
          </template>

          <el-table :data="mergedRows" border stripe size="small" max-height="300">
            <el-table-column prop="field" label="字段" width="120" />
            <el-table-column prop="orderVal" label="订单数据" min-width="140" />
            <el-table-column prop="piVal" label="PI数据" min-width="140" />
            <el-table-column prop="mergedVal" label="合并结果" min-width="140">
              <template #default="{ row }">
                <span :class="row.source ? 'source-' + row.source : ''">{{ row.mergedVal }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 包装计算结果 -->
        <el-card class="preview-card" style="margin-top: 16px;">
          <template #header>
            <div class="card-header">
              <span>包装计算</span>
              <el-button v-if="orderForm.order_requirement" size="small" type="primary" @click="runPackagingCalc">
                重新计算
              </el-button>
            </div>
          </template>

          <div v-if="!packagingResult" class="pkg-placeholder">
            <p v-if="orderForm.order_requirement">正在解析订单要求并计算...</p>
            <p v-else>请先填写订单要求，再点击「重新计算」</p>
          </div>

          <div v-else class="pkg-result">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="包装类型">{{ packagingResult.packaging_type }}</el-descriptions-item>
              <el-descriptions-item label="卡板规格">{{ packagingResult.pallet_spec || '无卡板' }}</el-descriptions-item>
              <el-descriptions-item label="总桶数">{{ packagingResult.drums }}</el-descriptions-item>
              <el-descriptions-item label="卡板数">{{ packagingResult.pallets }}</el-descriptions-item>
              <el-descriptions-item label="每板桶数">{{ packagingResult.drums_per_pallet }}</el-descriptions-item>
              <el-descriptions-item label="20GP判定">
                <el-tag :type="packagingResult.fits_20gp === '适合' ? 'success' : 'danger'" size="small">
                  {{ packagingResult.fits_20gp }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="产品净重">{{ packagingResult.net_weight_kg }} kg</el-descriptions-item>
              <el-descriptions-item label="总毛重">{{ packagingResult.gross_weight_kg }} kg</el-descriptions-item>
              <el-descriptions-item label="总体积" :span="2">{{ packagingResult.volume_cbm }} CBM</el-descriptions-item>
            </el-descriptions>
            <div v-if="packagingResult.packing_scheme" class="packing-scheme">
              <p>{{ packagingResult.packing_scheme }}</p>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="action-bar">
      <el-button @click="handleReset">重置</el-button>
      <el-button @click="runPackagingCalc" :disabled="!orderParsed">计算包装</el-button>
      <el-button
        type="primary"
        size="large"
        :disabled="!canMerge"
        :loading="saving"
        @click="handleConfirmSave"
      >
        确认入库
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import PasteTextarea from '@/components/phase1/PasteTextarea.vue'
import PiUploadDragger from '@/components/phase1/PiUploadDragger.vue'
import { ordersApi, type ParsedOrderSchema } from '@/api/orders'
import { uploadPiFile, type PiUploadResponse } from '@/api/pi'
import { saveOrderPiRecord, type PackagingResult } from '@/api/phase1'

// ─── State ────────────────────────────────────────────────────────────────────

const orderText = ref('')
const orderParsed = ref(false)
const orderParsedData = ref<ParsedOrderSchema | null>(null)

const piParsed = ref(false)
const piParsedData = ref<PiUploadResponse | null>(null)

const saving = ref(false)
const packagingResult = ref<PackagingResult | null>(null)

// ─── Order Form ───────────────────────────────────────────────────────────────

const orderForm = ref({
  order_no: '',
  customer_code: '',
  internal_code: '',
  product_cn: '',
  spec_kg: 0,
  quantity_kg: 0,
  unit_price: 0,
  total_amount: 0,
  hs_code: '',
  customs_name: '',
  order_requirement: '',
  notes: '',
})

// ─── PI Form ──────────────────────────────────────────────────────────────────

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
})

// ─── Computed ─────────────────────────────────────────────────────────────────

const canMerge = computed(() => orderParsed.value && orderForm.value.internal_code)

// ─── Merged Rows ───────────────────────────────────────────────────────────────

const mergedRows = computed(() => {
  const rows = [
    { field: '订单号', orderVal: orderForm.value.order_no, piVal: '', mergedVal: orderForm.value.order_no, source: 'order' },
    { field: '客户编码', orderVal: orderForm.value.customer_code, piVal: piForm.value.customer_code, mergedVal: orderForm.value.customer_code || piForm.value.customer_code, source: orderForm.value.customer_code ? 'order' : 'pi' },
    { field: '内部编码', orderVal: orderForm.value.internal_code, piVal: piForm.value.internal_code, mergedVal: orderForm.value.internal_code, source: 'order' },
    { field: '产品名称', orderVal: orderForm.value.product_cn, piVal: '', mergedVal: orderForm.value.product_cn, source: 'order' },
    { field: '规格kg', orderVal: String(orderForm.value.spec_kg), piVal: '', mergedVal: String(orderForm.value.spec_kg), source: 'order' },
    { field: '数量kg', orderVal: String(orderForm.value.quantity_kg), piVal: String(piForm.value.quantity), mergedVal: String(piForm.value.quantity || orderForm.value.quantity_kg), source: piForm.value.quantity ? 'pi' : 'order' },
    { field: '单价', orderVal: String(orderForm.value.unit_price), piVal: String(piForm.value.unit_price), mergedVal: String(piForm.value.unit_price || orderForm.value.unit_price), source: piForm.value.unit_price ? 'pi' : 'order' },
    { field: '金额', orderVal: String(orderForm.value.total_amount), piVal: String(piForm.value.total_amount), mergedVal: String(piForm.value.total_amount || orderForm.value.total_amount), source: piForm.value.total_amount ? 'pi' : 'order' },
    { field: 'H.S.Code', orderVal: orderForm.value.hs_code, piVal: piForm.value.hs_code, mergedVal: piForm.value.hs_code || orderForm.value.hs_code, source: piForm.value.hs_code ? 'pi' : 'order' },
    { field: '报关品名', orderVal: orderForm.value.customs_name, piVal: piForm.value.customs_name, mergedVal: orderForm.value.customs_name || piForm.value.customs_name, source: orderForm.value.customs_name ? 'order' : 'pi' },
    { field: '订单要求', orderVal: orderForm.value.order_requirement, piVal: '', mergedVal: orderForm.value.order_requirement, source: 'order' },
  ]
  return rows
})

// ─── Handlers ─────────────────────────────────────────────────────────────────

async function handleOrderParse(text: string) {
  try {
    const result = await ordersApi.parsePaste(text)
    if (result.orders.length === 0) {
      ElMessage.warning('未解析到订单数据')
      return
    }
    const first = result.orders[0]
    orderParsedData.value = first

    const firstItem = first.items[0] || {}
    orderForm.value = {
      order_no: first.order_no || '',
      customer_code: first.customer_code || '',
      internal_code: firstItem.internal_code || '',
      product_cn: firstItem.product_cn || '',
      spec_kg: firstItem.spec_kg || 0,
      quantity_kg: firstItem.quantity_kg || 0,
      unit_price: firstItem.unit_price || 0,
      total_amount: firstItem.total_amount || 0,
      hs_code: firstItem.hs_code || '',
      customs_name: firstItem.customs_name || '',
      order_requirement: (firstItem as any).order_requirement || '',
      notes: (firstItem as any).warning || '',
    }
    orderParsed.value = true

    // 自动触发包装计算
    if (orderForm.value.order_requirement) {
      runPackagingCalc()
    }

    ElMessage.success('订单解析成功')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '解析失败')
  }
}

async function handlePiFileSelected(file: File) {
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
    }
    piParsed.value = true
    ElMessage.success('PI 解析成功')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || 'PI 解析失败')
  }
}

function handleOrderClear() {
  orderParsed.value = false
  orderParsedData.value = null
  orderForm.value = { order_no: '', customer_code: '', internal_code: '', product_cn: '', spec_kg: 0, quantity_kg: 0, unit_price: 0, total_amount: 0, hs_code: '', customs_name: '', order_requirement: '', notes: '' }
  packagingResult.value = null
}

// ─── Packaging Calculation ─────────────────────────────────────────────────────

async function runPackagingCalc() {
  if (!orderForm.value.internal_code && !orderParsed.value) {
    ElMessage.warning('请先完成订单解析')
    return
  }

  const req = orderForm.value.order_requirement || ''
  const parsed = parseRequirement(req)
  const packagingName = parsed.packagingType || '125kg新款胶桶'
  const palletSpec = parsed.palletSpec === '1.0m*1.0m' ? '1.0x1.0' : '1.1x1.1'
  const noPallet = parsed.noPallet ? 'true' : 'false'
  const quantity = orderForm.value.quantity_kg || 0

  try {
    const resp = await fetch(
      `/api/v1/packages/calculate?mode=manual&quantity_kg=${quantity}&packaging_name=${encodeURIComponent(packagingName)}&pallet_spec=${palletSpec}&no_pallet=${noPallet}&transport_mode=sea`
    )
    if (!resp.ok) throw new Error('计算失败')
    const result = await resp.json()

    const container = result.container || {}
    packagingResult.value = {
      packaging_type: result.packaging?.name || packagingName,
      pallet_spec: result.packaging?.pallet_spec || palletSpec,
      drums: result.drums || 0,
      pallets: result.pallets || 0,
      drums_per_pallet: result.packaging?.pallet_capacity || 5,
      net_weight_kg: Math.round((orderForm.value.quantity_kg || 0) * 0.95),
      gross_weight_kg: result.total_weight_kg || 0,
      volume_cbm: result.total_cbm || 0,
      fits_20gp: container.recommended === '20GP' ? '适合' : '超出',
      load_rate: container.load_rate,
      packing_scheme: result.packing_scheme || '',
      no_pallet: parsed.noPallet || false,
    }
  } catch (err) {
    ElMessage.error('包装计算失败')
  }
}

interface ParsedRequirement {
  packagingType?: string
  palletSpec?: string
  drumsPerPallet?: number
  noPallet?: boolean
}

function parseRequirement(text: string): ParsedRequirement {
  const result: ParsedRequirement = {}

  // 桶规格匹配
  const drumMatch = text.match(/(\d+)\s*kg\s*(桶|桶装)/)
  if (drumMatch) {
    const kg = parseInt(drumMatch[1])
    const drumMap: Record<number, string> = {
      25: '25kg正方罐', 30: '30kg蓝桶', 50: '50kg蓝桶(大口)',
      60: '60kg蓝桶', 125: '125kg新款胶桶', 150: '150kg新款胶桶', 200: '200kg双环闭口桶',
    }
    result.packagingType = drumMap[kg] || `${kg}kg桶`
  }

  // 卡板规格匹配
  if (text.includes('1.1m') || text.includes('1.1*1.1')) {
    result.palletSpec = '1.1m*1.1m'
  } else if (text.includes('1.0m') || text.includes('1.0*1.0')) {
    result.palletSpec = '1.0m*1.0m'
  }

  // 不打卡板
  if (text.includes('不打卡板') || text.includes('散货')) {
    result.noPallet = true
  }

  return result
}

// ─── Confirm Save ──────────────────────────────────────────────────────────────

async function handleConfirmSave() {
  if (!canMerge.value) {
    ElMessage.warning('请确保订单已解析')
    return
  }

  saving.value = true
  try {
    const orderData = {
      order_no: orderForm.value.order_no,
      customer_code: orderForm.value.customer_code,
      internal_code: orderForm.value.internal_code,
      product_cn: orderForm.value.product_cn,
      spec_kg: orderForm.value.spec_kg,
      quantity_kg: orderForm.value.quantity_kg,
      unit_price: orderForm.value.unit_price,
      total_amount: orderForm.value.total_amount,
      hs_code: orderForm.value.hs_code,
      customs_name: orderForm.value.customs_name,
      order_requirement: orderForm.value.order_requirement,
      notes: orderForm.value.notes,
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

    await saveOrderPiRecord({
      order_data: orderData,
      pi_data: piData,
      packaging_result: packagingResult.value || undefined,
    })

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
  packagingResult.value = null
  orderForm.value = { order_no: '', customer_code: '', internal_code: '', product_cn: '', spec_kg: 0, quantity_kg: 0, unit_price: 0, total_amount: 0, hs_code: '', customs_name: '', order_requirement: '', notes: '' }
  piForm.value = { pi_no: '', customer_code: '', pi_date: '', internal_code: '', quantity: 0, unit_price: 0, total_amount: 0, hs_code: '', customs_name: '' }
}
</script>

<style scoped>
.phase1-workflow { padding: 24px; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: #909399; margin: 0; }

.workflow-layout { display: grid; grid-template-columns: 420px 1fr; gap: 20px; align-items: start; }
.input-panel { display: flex; flex-direction: column; }
.preview-panel { display: flex; flex-direction: column; }

.input-card, .preview-card { border-radius: 12px; }
.card-header { font-weight: 600; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }

.order-preview, .pi-preview { margin-top: 12px; }

.pkg-placeholder { text-align: center; color: #909399; padding: 20px; }
.pkg-result { padding: 4px 0; }
.packing-scheme { margin-top: 12px; padding: 10px; background: #f5f7fa; border-radius: 6px; font-size: 13px; color: #606266; }

.action-bar { position: sticky; bottom: 0; display: flex; justify-content: flex-end; gap: 12px; padding: 16px 24px; background: white; border-top: 1px solid #e8e8e8; margin-top: 20px; box-shadow: 0 -2px 12px rgba(0,0,0,0.05); }

.source-order { color: #409eff; }
.source-pi { color: #67c23a; }
</style>