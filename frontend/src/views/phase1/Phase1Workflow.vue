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

    <!-- 重复产品提示弹窗 -->
    <DuplicateWarningDialog
      v-model="duplicateDialogVisible"
      :duplicates="duplicateItems"
      @confirm="handleConfirmSave"
      @cancel="handleDuplicateCancel"
    />

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
            <div class="summary-row"><span class="label">币制：</span>{{ piFileData.currency || '-' }}</div>
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

        <!-- 头部信息（可编辑） -->
        <div class="preview-header">
          <div class="preview-section">
            <h4 class="section-title">PI合同表信息</h4>
            <div class="field-grid">
              <div class="field-item"><span class="label">订单号</span><el-input v-model="mergePreviewData.order_no" size="small" /></div>
              <div class="field-item"><span class="label">客户编码</span><el-input v-model="mergePreviewData.customer_code" size="small" clearable /></div>
              <div class="field-item"><span class="label">业务员</span><el-input v-model="mergePreviewData.sales_person" size="small" clearable /></div>
              <div class="field-item"><span class="label">PI日期</span><el-input v-model="mergePreviewData.pi_date" size="small" clearable /></div>
              <div class="field-item"><span class="label">出货抬头</span><el-input v-model="mergePreviewData.pi_contract_shipment_title" size="small" clearable /></div>
              <div class="field-item"><span class="label">运输方式</span><el-input v-model="mergePreviewData.pi_contract_shipment_method" size="small" clearable /></div>
            </div>
          </div>

          <div class="preview-section">
            <h4 class="section-title">销售订单表信息</h4>
            <div class="field-grid">
              <div class="field-item"><span class="label">PI号</span><el-input v-model="mergePreviewData.sales_order_no" size="small" clearable /></div>
              <div class="field-item"><span class="label">出货抬头</span><el-input v-model="mergePreviewData.shipment_title" size="small" clearable /></div>
              <div class="field-item"><span class="label">跟单员</span><el-input v-model="mergePreviewData.merchandiser" size="small" clearable /></div>
              <div class="field-item"><span class="label">交货日期</span><el-input v-model="mergePreviewData.delivery_date" size="small" clearable /></div>
              <div class="field-item"><span class="label">运输方式</span><el-input v-model="mergePreviewData.shipment_method" size="small" clearable /></div>
            </div>
          </div>

          <div class="preview-section">
            <h4 class="section-title">PI合同文件信息</h4>
            <div class="field-grid">
              <div class="field-item"><span class="label">收货人</span><el-input v-model="mergePreviewData.consignee_name" size="small" clearable /></div>
              <div class="field-item"><span class="label">收货地址</span><el-input v-model="mergePreviewData.consignee_address" size="small" clearable /></div>
              <div class="field-item"><span class="label">电话</span><el-input v-model="mergePreviewData.consignee_tel" size="small" clearable /></div>
              <div class="field-item"><span class="label">目的港</span><el-input v-model="mergePreviewData.destination" size="small" clearable /></div>
              <div class="field-item"><span class="label">装货港</span><el-input v-model="mergePreviewData.loading_port" size="small" clearable /></div>
              <div class="field-item"><span class="label">价格条款</span><el-input v-model="mergePreviewData.price_term" size="small" clearable /></div>
              <div class="field-item"><span class="label">币制</span><el-input v-model="mergePreviewData.currency" size="small" clearable /></div>
              <div class="field-item"><span class="label">付款方式</span><el-input v-model="mergePreviewData.payment_terms" size="small" clearable /></div>
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

        <!-- 产品明细表（可编辑） -->
        <el-table :data="mergePreviewData.items" border stripe size="small" max-height="400" style="margin-top: 16px">
          <el-table-column prop="internal_code" label="内部编码" width="110" fixed>
            <template #default="{ row }">
              <el-input v-model="row.internal_code" size="small" />
            </template>
          </el-table-column>
          <el-table-column prop="product_cn" label="产品名称" min-width="130">
            <template #default="{ row }">
              <el-input v-model="row.product_cn" size="small" />
            </template>
          </el-table-column>
          <el-table-column prop="spec_kg" label="规格kg" width="90" align="center">
            <template #default="{ row }">
              <el-input-number v-model="row.spec_kg" size="small" :controls="false" :precision="2" style="width:100%" />
            </template>
          </el-table-column>
          <el-table-column prop="quantity_kg" label="数量(kg)" width="100" align="center">
            <template #default="{ row }">
              <el-input-number v-model="row.quantity_kg" size="small" :controls="false" :precision="2" style="width:100%" @change="calcRowAmount(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="unit_price" label="单价" width="90" align="center">
            <template #default="{ row }">
              <el-input-number v-model="row.unit_price" size="small" :controls="false" :precision="2" style="width:100%" @change="calcRowAmount(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="total_amount" label="金额" width="100" align="center">
            <template #default="{ row }">
              <el-input-number v-model="row.total_amount" size="small" :controls="false" :precision="2" style="width:100%" />
            </template>
          </el-table-column>
          <el-table-column prop="hs_code" label="H.S.Code" width="110">
            <template #default="{ row }">
              <el-input v-model="row.hs_code" size="small" :class="{ 'is-warning': !row.hs_code }" />
            </template>
          </el-table-column>
          <el-table-column prop="customs_name" label="报关品名" min-width="130">
            <template #default="{ row }">
              <el-input v-model="row.customs_name" size="small" :class="{ 'is-warning': !row.customs_name }" />
            </template>
          </el-table-column>
          <el-table-column prop="customs_ingredients" label="报关成分" min-width="150">
            <template #default="{ row }">
              <el-input v-model="row.customs_ingredients" size="small" />
            </template>
          </el-table-column>
          <el-table-column prop="product_appearance" label="产品外观" min-width="100">
            <template #default="{ row }">
              <el-input v-model="row.product_appearance" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="来源" width="130" align="center">
            <template #default="{ row }">
              <el-select v-model="row.source_note" size="small" style="width:100%">
                <el-option label="匹配" value="匹配" />
                <el-option label="仅PI合同表" value="仅PI合同表" />
                <el-option label="仅销售订单表" value="仅销售订单表" />
                <el-option label="PI文件" value="PI文件" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="60" fixed="right" align="center">
            <template #default="{ $index }">
              <el-button type="danger" text size="small" @click="removeMergeItem($index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button size="small" type="primary" text @click="addMergeItem" style="margin-top: 8px">
          <el-icon><Plus /></el-icon> 添加产品
        </el-button>
        <div style="display:flex; justify-content:flex-end; margin-top: 12px">
          <el-button type="primary" size="small" @click="handleShowPackaging">包装计算</el-button>
        </div>
      </el-card>
    </div>

    <!-- 包装计算（点击按钮后展开） -->
    <div v-if="showPackaging" class="packaging-section">
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
import { Document, Delete, Plus } from '@element-plus/icons-vue'
import PasteTextarea from '@/components/phase1/PasteTextarea.vue'
import PiUploadDragger from '@/components/phase1/PiUploadDragger.vue'
import PackagingCalculator from '@/components/phase1/PackagingCalculator.vue'
import DuplicateWarningDialog from '@/components/phase1/DuplicateWarningDialog.vue'
import {
  ordersApi,
  type ParsedOrderSchema,
  type MergePreviewResponse,
  type LedgerWriteRequest,
  type DuplicateItem,
} from '@/api/orders'
import { uploadPiFile, type PiUploadResponse } from '@/api/pi'
import { nameMappingApi } from '@/api/name_mapping'

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

// 重复检测
const duplicateDialogVisible = ref(false)
const duplicateItems = ref<DuplicateItem[]>([])
const pendingSaveRequest = ref<LedgerWriteRequest | null>(null)

// 包装计算
const calcRef = ref<InstanceType<typeof PackagingCalculator>>()
const showPackaging = ref(false)

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
    showPackaging.value = false

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
          product_en: '',
          spec_kg: item.spec_kg ?? undefined,
          quantity_kg: item.quantity_kg,
          unit_price: item.unit_price,
          total_amount: item.total_amount,
          hs_code: item.hs_code,
          customs_name: item.customs_name,
          customs_ingredients: item.customs_ingredients,
          product_appearance: item.product_appearance,
          packaging_name: rowCalc.packaging_name || undefined,
          drum_count: rowCalc.drums ?? undefined,
          pallet_count: rowCalc.pallets ?? (rowCalc.drums && rowCalc.drums_per_pallet ? Math.ceil(rowCalc.drums / rowCalc.drums_per_pallet) : undefined),
          net_weight_kg: rowCalc.net_weight_kg ?? undefined,
          gross_weight_kg: rowCalc.gross_weight_kg ?? undefined,
          volume_cbm: rowCalc.volume_cbm ?? undefined,
          fits_20gp: rowCalc.fits_20gp || undefined,
          packaging_type_id: undefined,
          pallet_spec: rowCalc.pallet_spec || undefined,
          drums_per_pallet: rowCalc.drums_per_pallet ?? undefined,
        }
      })

    // 查询英文名
    for (const item of items) {
      const cn = item.customs_name || item.product_cn || ''
      if (cn) {
        try {
          const res = await nameMappingApi.lookupByCn(cn)
          if (res.data.en) item.product_en = res.data.en
        } catch { /* ignore */ }
      }
    }

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
      currency: preview.currency,
      // 从销售订单表补充（取第一条订单的数据）
      ...buildSalesOrderFields(),
      items,
    }

    // 先检查重复
    const checkResult = await ordersApi.checkDuplicates({ items })
    if (checkResult.has_duplicates) {
      duplicateItems.value = checkResult.duplicates
      pendingSaveRequest.value = request
      duplicateDialogVisible.value = true
      saving.value = false
      return
    }

    // 无重复，直接写入
    await doWriteLedger(request)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '写入台账失败')
  } finally {
    saving.value = false
  }
}

async function doWriteLedger(request: LedgerWriteRequest) {
  saving.value = true
  try {
    const resp = await ordersApi.writeLedger(request)
    savedRecordId.value = resp.record_id
    ElMessage.success(`成功写入台账：${resp.items_count} 条产品记录`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '写入台账失败')
  } finally {
    saving.value = false
  }
}

async function handleConfirmSave() {
  if (pendingSaveRequest.value) {
    await doWriteLedger(pendingSaveRequest.value)
    pendingSaveRequest.value = null
  }
}

function handleDuplicateCancel() {
  pendingSaveRequest.value = null
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

function calcRowAmount(row: any) {
  const qty = Number(row.quantity_kg) || 0
  const price = Number(row.unit_price) || 0
  row.total_amount = Math.round(qty * price * 100) / 100
}

async function handleShowPackaging() {
  showPackaging.value = true
  await nextTick()
  if (calcRef.value && mergePreviewData.value?.items.length) {
    calcRef.value.clearRows()
    for (const item of mergePreviewData.value.items) {
      calcRef.value.addRow(item.internal_code, item.product_cn || '', item.quantity_kg || 0)
    }
  }
}

function addMergeItem() {
  if (!mergePreviewData.value) return
  mergePreviewData.value.items.push({
    internal_code: '',
    source_pi_contract: false,
    source_sales_order: false,
    source_pi_file: false,
    source_note: '',
    product_cn: '',
    spec_kg: undefined,
    quantity_kg: undefined,
    unit_price: undefined,
    total_amount: undefined,
    hs_code: '',
    customs_name: '',
    customs_ingredients: '',
    product_appearance: '',
    validation_status: 'ok',
    warnings: [],
  })
}

function removeMergeItem(index: number) {
  if (!mergePreviewData.value) return
  mergePreviewData.value.items.splice(index, 1)
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
  showPackaging.value = false
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
.field-item { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.field-item .label { color: #909399; min-width: 60px; flex-shrink: 0; }
.field-item :deep(.el-input) { flex: 1; min-width: 0; }

/* 编辑表格中的警告输入框 */
.is-warning :deep(.el-input__wrapper) { box-shadow: 0 0 0 1px #e6a23c inset; }

/* 包装区 */
.packaging-section { margin-top: 16px; }

/* 警告文字 */
.text-warning { color: #e6a23c; font-style: italic; }
.validation-warn { font-size: 13px; margin-top: 4px; }
</style>
