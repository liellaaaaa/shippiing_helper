<template>
  <div class="phase1-workflow">
    <!-- 页头 -->
    <div class="page-header">
      <h1 class="page-title">外贸订单处理工作流</h1>
      <div class="page-header-row">
        <span class="page-subtitle">PI合同表 + 销售订单表（粘贴）→ PI合同文件（上传）→ 预览合并 → 确认入库</span>
        <div class="header-actions">
          <el-button size="small" @click="handleReset">重置</el-button>
          <el-button type="primary" size="small" :disabled="!canPreview" :loading="previewing" @click="handlePreview">
            预览合并
          </el-button>
          <el-button
            type="success"
            size="small"
            :disabled="!canSave"
            :loading="saving"
            v-track="{ event: 'save_to_ledger', module: 'phase1' }"
            @click="handleSaveLedger"
          >
            确认入库
          </el-button>
          <el-button
            v-if="savedRecordId"
            type="primary"
            size="small"
            @click="$router.push({ path: '/dashboard' })"
          >
            进入台账 →
          </el-button>
        </div>
      </div>
    </div>

    <!-- 三列输入区 -->
    <div class="three-col-layout">
      <!-- 第一列：PI合同表 -->
      <div class="input-col">
        <el-card class="input-card">
          <template #header>
            <div class="card-header">
              <span>PI合同表</span>
              <el-tag v-if="piContractParsed" type="success" size="small">已解析</el-tag>
            </div>
          </template>
          <PasteTextarea
            v-model="piContractText"
            @parse="handlePiContractParse"
            @clear="piContractText = ''; piContractParsed = false; piContractOrders = []"
          />
          <div v-if="piContractOrders.length > 0" class="parse-summary">
            <span>订单号：{{ piContractOrders[0]?.order_no }}</span>
            <span>，产品 {{ piContractOrders[0]?.items?.length || 0 }} 种</span>
          </div>
        </el-card>
      </div>

      <!-- 第二列：销售订单表 -->
      <div class="input-col">
        <el-card class="input-card">
          <template #header>
            <div class="card-header">
              <span>销售订单表</span>
              <el-tag v-if="salesOrderParsed" type="success" size="small">已解析</el-tag>
            </div>
          </template>
          <PasteTextarea
            v-model="salesOrderText"
            @parse="handleSalesOrderParse"
            @clear="salesOrderText = ''; salesOrderParsed = false; salesOrderOrders = []"
          />
          <div v-if="salesOrderOrders.length > 0" class="parse-summary">
            <span>订单号：{{ salesOrderOrders[0]?.order_no }}</span>
            <span>，产品 {{ salesOrderOrders[0]?.items?.length || 0 }} 种</span>
          </div>
        </el-card>
      </div>

      <!-- 第三列：PI合同文件上传 -->
      <div class="input-col">
        <el-card class="input-card">
          <template #header>
            <div class="card-header">
              <span>PI合同文件</span>
              <el-tag v-if="piFileUploaded" type="success" size="small">已上传</el-tag>
            </div>
          </template>
          <PiUploadDragger
            v-if="!piFileUploaded"
            @fileSelected="handlePiFileSelected"
          />
          <div v-else class="pi-file-info">
            <el-icon><document /></el-icon>
            <span class="pi-file-name">{{ piFileName }}</span>
            <el-button text size="small" @click="piFileUploaded = false; piFileName = ''; piFileData = null">
              重新上传
            </el-button>
          </div>
          <!-- PI文件解析结果显示 -->
          <div v-if="piFileData" class="pi-file-summary">
            <div class="summary-row"><span class="label">PI号：</span>{{ piFileData.pi_no }}</div>
            <div class="summary-row"><span class="label">目的港：</span>{{ piFileData.destination || '-' }}</div>
            <div class="summary-row"><span class="label">收货人：</span>{{ piFileData.consignee_name || '-' }}</div>
            <div class="summary-row"><span class="label">价格条款：</span>{{ piFileData.price_term || '-' }}</div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 合并预览区 -->
    <div v-if="mergePreviewData" class="merge-preview-panel">
      <!-- 校验警告 -->
      <el-alert
        v-if="mergePreviewData.validation_status === 'warning'"
        type="warning"
        :closable="true"
        style="margin-bottom: 12px"
      >
        <template #title>
          存在数据不一致，请核对后再入库
        </template>
        <div v-for="w in mergePreviewData.validation_warnings" :key="w.field + w.internal_code" class="validation-warn">
          <strong>{{ w.internal_code }}</strong>：{{ w.message }}
        </div>
      </el-alert>

      <el-card>
        <template #header>
          <div class="card-header">
            <span>合并预览</span>
            <el-tag :type="mergePreviewData.validation_status === 'ok' ? 'success' : 'warning'" size="small">
              {{ mergePreviewData.validation_status === 'ok' ? '校验通过' : '存在不一致' }}
            </el-tag>
          </div>
        </template>

        <!-- 头部信息 -->
        <div class="preview-header">
          <div class="preview-section">
            <h4 class="section-title">PI合同表信息</h4>
            <div class="field-grid">
              <div class="field-item"><span class="label">订单号</span><span class="value">{{ mergePreviewData.order_no }}</span></div>
              <div class="field-item"><span class="label">客户编码</span><span class="value">{{ mergePreviewData.customer_code || '-' }}</span></div>
              <div class="field-item"><span class="label">业务员</span><span class="value">{{ mergePreviewData.sales_person || '-' }}</span></div>
              <div class="field-item"><span class="label">PI日期</span><span class="value">{{ mergePreviewData.pi_date || '-' }}</span></div>
              <div class="field-item"><span class="label">出货抬头</span><span class="value">{{ mergePreviewData.pi_contract_shipment_title || '-' }}</span></div>
              <div class="field-item"><span class="label">运输方式</span><span class="value">{{ mergePreviewData.pi_contract_shipment_method || '-' }}</span></div>
            </div>
          </div>

          <div class="preview-section">
            <h4 class="section-title">销售订单表信息</h4>
            <div class="field-grid">
              <div class="field-item"><span class="label">PI号</span><span class="value">{{ mergePreviewData.sales_order_no || '-' }}</span></div>
              <div class="field-item"><span class="label">出货抬头</span><span class="value">{{ mergePreviewData.shipment_title || '-' }}</span></div>
              <div class="field-item"><span class="label">跟单员</span><span class="value">{{ mergePreviewData.merchandiser || '-' }}</span></div>
              <div class="field-item"><span class="label">交货日期</span><span class="value">{{ mergePreviewData.delivery_date || '-' }}</span></div>
              <div class="field-item"><span class="label">运输方式</span><span class="value">{{ mergePreviewData.shipment_method || '-' }}</span></div>
            </div>
          </div>

          <div class="preview-section">
            <h4 class="section-title">PI合同文件信息</h4>
            <div class="field-grid">
              <div class="field-item"><span class="label">收货人</span><span class="value">{{ mergePreviewData.consignee_name || '-' }}</span></div>
              <div class="field-item"><span class="label">收货地址</span><span class="value">{{ mergePreviewData.consignee_address || '-' }}</span></div>
              <div class="field-item"><span class="label">电话</span><span class="value">{{ mergePreviewData.consignee_tel || '-' }}</span></div>
              <div class="field-item"><span class="label">目的港</span><span class="value">{{ mergePreviewData.destination || '-' }}</span></div>
              <div class="field-item"><span class="label">装货港</span><span class="value">{{ mergePreviewData.loading_port || '-' }}</span></div>
              <div class="field-item"><span class="label">价格条款</span><span class="value">{{ mergePreviewData.price_term || '-' }}</span></div>
              <div class="field-item"><span class="label">付款方式</span><span class="value">{{ mergePreviewData.payment_terms || '-' }}</span></div>
            </div>
          </div>
        </div>

        <!-- 产品匹配统计 -->
        <div class="match-summary" v-if="mergePreviewData.total_products">
          <el-tag type="info" size="small">共 {{ mergePreviewData.total_products }} 个产品</el-tag>
          <el-tag type="success" size="small" style="margin-left:8px">匹配 {{ mergePreviewData.matched_count }} 个</el-tag>
          <el-tag type="warning" size="small" style="margin-left:8px" v-if="(mergePreviewData.pi_only_count ?? 0) > 0">仅PI合同表 {{ mergePreviewData.pi_only_count }} 个</el-tag>
          <el-tag type="danger" size="small" style="margin-left:8px" v-if="(mergePreviewData.sales_only_count ?? 0) > 0">仅销售订单表 {{ mergePreviewData.sales_only_count }} 个</el-tag>
        </div>

        <!-- 产品明细表 -->
        <el-table :data="mergePreviewData.items" border stripe size="small" max-height="350" style="margin-top: 16px">
          <el-table-column prop="internal_code" label="内部编码" width="110" fixed />
          <el-table-column prop="product_cn" label="产品名称" min-width="130" show-overflow-tooltip />
          <el-table-column prop="spec_kg" label="规格kg" width="80" align="center">
            <template #default="{ row }">{{ row.spec_kg ?? '-' }}</template>
          </el-table-column>
          <el-table-column prop="quantity_kg" label="数量(kg)" width="90" align="center" />
          <el-table-column prop="unit_price" label="单价" width="80" align="center">
            <template #default="{ row }">{{ row.unit_price ?? '-' }}</template>
          </el-table-column>
          <el-table-column prop="total_amount" label="金额" width="90" align="center">
            <template #default="{ row }">{{ row.total_amount ?? '-' }}</template>
          </el-table-column>
          <el-table-column prop="hs_code" label="H.S.Code" width="110">
            <template #default="{ row }">
              <span :class="{ 'text-warning': !row.hs_code }">{{ row.hs_code || '待填充' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="customs_name" label="报关品名" min-width="130" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="{ 'text-warning': !row.customs_name }">{{ row.customs_name || '待填充' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="customs_ingredients" label="报关成分" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.customs_ingredients || '-' }}</template>
          </el-table-column>
          <el-table-column prop="product_appearance" label="产品外观" min-width="100" show-overflow-tooltip>
            <template #default="{ row }">{{ row.product_appearance || '-' }}</template>
          </el-table-column>
          <el-table-column label="来源" width="130" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.source_note === '匹配'" size="small" type="success">匹配</el-tag>
              <el-tag v-else-if="row.source_note === '仅PI合同表'" size="small" type="warning">仅PI合同表</el-tag>
              <el-tag v-else-if="row.source_note === '仅销售订单表'" size="small" type="danger">仅订单表</el-tag>
              <el-tag v-else-if="row.source_pi_file" size="small" type="info">PI文件</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 包装计算（入库前可选） -->
    <div v-if="mergePreviewData" class="packaging-section">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>包装计算</span>
          </div>
        </template>
        <PackagingCalculator ref="calcRef" />
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import PasteTextarea from '@/components/phase1/PasteTextarea.vue'
import PiUploadDragger from '@/components/phase1/PiUploadDragger.vue'
import PackagingCalculator from '@/components/phase1/PackagingCalculator.vue'
import {
  ordersApi,
  type ParsedOrderSchema,
  type MergePreviewResponse,
  type LedgerWriteRequest,
} from '@/api/orders'
import { uploadPiFile, type PiUploadResponse } from '@/api/pi'

// ── State ────────────────────────────────────────────────────────────────────

// PI合同表
const piContractText = ref('')
const piContractParsed = ref(false)
const piContractOrders = ref<ParsedOrderSchema[]>([])

// 销售订单表
const salesOrderText = ref('')
const salesOrderParsed = ref(false)
const salesOrderOrders = ref<ParsedOrderSchema[]>([])

// PI合同文件
const piFileUploaded = ref(false)
const piFileName = ref('')
const piFileData = ref<PiUploadResponse | null>(null)
const piFileForUpload = ref<File | null>(null)

// 合并预览
const mergePreviewData = ref<MergePreviewResponse | null>(null)
const previewing = ref(false)

// 保存
const saving = ref(false)
const savedRecordId = ref<number | null>(null)

// 包装计算
const calcRef = ref<InstanceType<typeof PackagingCalculator>>()

// ── Computed ─────────────────────────────────────────────────────────────────

const canPreview = computed(() =>
  (piContractParsed.value && piContractOrders.value.length > 0) ||
  (salesOrderParsed.value && salesOrderOrders.value.length > 0)
)

const canSave = computed(() => mergePreviewData.value !== null)

// ── Handlers ─────────────────────────────────────────────────────────────────

async function handlePiContractParse(text: string) {
  if (!text.trim()) {
    ElMessage.warning('PI合同表文本不能为空')
    return
  }
  try {
    const result = await ordersApi.parsePiContractTable(text)
    if (result.orders.length === 0) {
      ElMessage.warning('PI合同表未解析到数据')
      return
    }
    piContractOrders.value = result.orders
    piContractParsed.value = true
    ElMessage.success(`PI合同表解析成功：${result.orders[0].order_no}，${result.orders[0].items.length} 种产品`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || 'PI合同表解析失败')
  }
}

async function handleSalesOrderParse(text: string) {
  if (!text.trim()) {
    ElMessage.warning('销售订单表文本不能为空')
    return
  }
  try {
    const result = await ordersApi.parseSalesOrderTable(text)
    if (result.orders.length === 0) {
      ElMessage.warning('销售订单表未解析到数据')
      return
    }
    salesOrderOrders.value = result.orders
    salesOrderParsed.value = true
    ElMessage.success(`销售订单表解析成功：${result.orders[0].order_no}，${result.orders[0].items.length} 种产品`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '销售订单表解析失败')
  }
}

async function handlePiFileSelected(file: File) {
  piFileName.value = file.name
  piFileForUpload.value = file
  try {
    const result = await uploadPiFile(file)
    piFileData.value = result
    piFileUploaded.value = true
    ElMessage.success(`PI文件 "${file.name}" 解析成功`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || 'PI文件解析失败')
    piFileUploaded.value = false
    piFileForUpload.value = null
  }
}

async function handlePreview() {
  previewing.value = true
  try {
    const formData = new FormData()
    if (piContractText.value.trim()) {
      formData.append('pi_contract_table_text', piContractText.value)
    }
    if (salesOrderText.value.trim()) {
      formData.append('sales_order_table_text', salesOrderText.value)
    }
    if (piFileForUpload.value) {
      formData.append('pi_file', piFileForUpload.value)
    }

    const result = await ordersApi.mergePreview(formData)
    mergePreviewData.value = result

    // 等待 DOM 更新后同步到包装计算器（v-if="mergePreviewData" 导致组件延迟挂载）
    await nextTick()
    if (calcRef.value && result.items.length > 0) {
      calcRef.value.clearRows()
      for (const item of result.items) {
        calcRef.value.addRow(item.internal_code, item.product_cn || '', item.quantity_kg || 0)
      }
    }

    if (result.validation_status === 'ok') {
      ElMessage.success('三源合并完成，校验通过')
    } else {
      ElMessage.warning('存在数据不一致，请核对后入库')
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '合并预览失败')
  } finally {
    previewing.value = false
  }
}

async function handleSaveLedger() {
  if (!mergePreviewData.value) {
    ElMessage.warning('请先执行预览合并')
    return
  }
  saving.value = true
  try {
    const preview = mergePreviewData.value
    // 从计算器获取包装数据
    const calcSummary = calcRef.value?.getSummary()
    const calcRows = calcRef.value?.getRows() || []

    // 构建包装计算结果索引 {internal_code: calcRow}
    const calcMap: Record<string, any> = {}
    for (const row of calcRows) {
      const code = row.internal_code || row.product_name
      if (code) calcMap[code] = row
    }

    // 只写入包装计算器中有数据的产品（以包装计算结果为准）
    const items = preview.items
      .filter(item => calcMap[item.internal_code])
      .map(item => {
        const rowCalc = calcMap[item.internal_code] || {}
        return {
          internal_code: item.internal_code,
          product_cn: item.product_cn,
          spec_kg: item.spec_kg || undefined,
          quantity_kg: item.quantity_kg,
          unit_price: item.unit_price,
          total_amount: item.total_amount,
          hs_code: item.hs_code,
          customs_name: item.customs_name,
          customs_ingredients: item.customs_ingredients,
          product_appearance: item.product_appearance,
          drum_count: rowCalc.drums || undefined,
          pallet_count: rowCalc.pallets || (rowCalc.drums && rowCalc.drums_per_pallet ? Math.ceil(rowCalc.drums / rowCalc.drums_per_pallet) : undefined),
          net_weight_kg: rowCalc.net_weight_kg || undefined,
          gross_weight_kg: rowCalc.gross_weight_kg || undefined,
          volume_cbm: rowCalc.volume_cbm || undefined,
          fits_20gp: rowCalc.fits_20gp || undefined,
          packaging_type_id: undefined,
          pallet_spec: rowCalc.pallet_spec || undefined,
          drums_per_pallet: rowCalc.drums_per_pallet || undefined,
        }
      })

    // 检查是否有产品被写入
    if (items.length === 0) {
      ElMessage.warning('请先在包装计算器中添加产品并完成计算')
      return
    }

    const request: LedgerWriteRequest = {
      order_no: preview.order_no,
      customer_code: preview.customer_code,
      sales_person: preview.sales_person,
      pi_date: preview.pi_date,
      // PI合同文件字段
      consignee_name: preview.consignee_name,
      consignee_address: preview.consignee_address,
      consignee_tel: preview.consignee_tel,
      destination: preview.destination,
      loading_port: preview.loading_port,
      price_term: preview.price_term,
      payment_terms: preview.payment_terms,
      bank_info: preview.bank_info,
      // 从销售订单表补充（取第一条订单的数据）
      ...buildSalesOrderFields(),
      items,
    }

    const resp = await ordersApi.writeLedger(request)
    savedRecordId.value = resp.record_id
    ElMessage.success(`成功写入台账：${resp.items_count} 条产品记录`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '写入台账失败')
  } finally {
    saving.value = false
  }
}

function buildSalesOrderFields(): Partial<LedgerWriteRequest> {
  if (!salesOrderOrders.value.length) return {}
  const first = salesOrderOrders.value[0]
  const firstItem = first.items?.[0]
  if (!firstItem) return { sales_order_no: first.order_no }
  return {
    sales_order_no: first.order_no,
    order_date: firstItem.order_date_placed || undefined,
    delivery_date: firstItem.order_date || undefined,
    shipment_channel: firstItem.shipment_channel || undefined,
    shipment_method: firstItem.shipment_method || undefined,
    review_status: firstItem.review_status || undefined,
    spec_abnormal: firstItem.spec_abnormal || undefined,
    has_sample: firstItem.has_sample || undefined,
    price_adjusted: firstItem.price_adjusted || undefined,
    order_confirmed: firstItem.order_confirmed || undefined,
    production_deadline: firstItem.production_deadline || undefined,
    shipment_title: firstItem.shipment_title || undefined,
    document_type: firstItem.document_type || undefined,
    merchandiser: firstItem.merchandiser || undefined,
  }
}

function handleReset() {
  piContractText.value = ''
  piContractParsed.value = false
  piContractOrders.value = []
  salesOrderText.value = ''
  salesOrderParsed.value = false
  salesOrderOrders.value = []
  piFileUploaded.value = false
  piFileName.value = ''
  piFileData.value = null
  piFileForUpload.value = null
  mergePreviewData.value = null
  savedRecordId.value = null
  calcRef.value?.clearRows()
}
</script>

<style scoped>
.phase1-workflow { padding: 24px; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-header-row { display: flex; align-items: center; justify-content: space-between; }
.page-subtitle { font-size: 14px; color: #909399; margin: 0; }
.header-actions { display: flex; gap: 8px; }

/* 三列布局 */
.three-col-layout { display: flex; gap: 16px; }
.input-col { flex: 1; min-width: 0; }

/* 卡片 */
.input-card { border-radius: 12px; }
.card-header { font-weight: 600; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }

/* 解析摘要 */
.parse-summary { margin-top: 8px; font-size: 13px; color: #67c23a; }

/* PI文件信息 */
.pi-file-info { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: #f0f9eb; border-radius: 8px; color: #67c23a; }
.pi-file-name { flex: 1; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.pi-file-summary { margin-top: 12px; display: flex; flex-direction: column; gap: 4px; }
.summary-row { font-size: 13px; color: #606266; }
.summary-row .label { color: #909399; }

/* 合并预览 */
.merge-preview-panel { margin-top: 20px; }
.match-summary { margin: 12px 0; display: flex; align-items: center; }
.preview-header { display: flex; gap: 24px; }
.preview-section { flex: 1; }
.section-title { font-size: 14px; font-weight: 600; margin: 0 0 12px 0; color: #303133; }
.field-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.field-item { display: flex; gap: 8px; font-size: 13px; }
.field-item .label { color: #909399; min-width: 60px; }
.field-item .value { color: #303133; }

/* 包装区 */
.packaging-section { margin-top: 16px; }

/* 警告文字 */
.text-warning { color: #e6a23c; font-style: italic; }
.validation-warn { font-size: 13px; margin-top: 4px; }
</style>
