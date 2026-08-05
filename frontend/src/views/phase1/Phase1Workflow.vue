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
              <div class="field-item">
                <span class="label">付款方式</span>
                <el-tag v-if="mergePreviewData.payment_method === 'TT'" size="small" type="success" style="margin-right:6px">TT</el-tag>
                <el-tag v-else-if="mergePreviewData.payment_method === 'LC'" size="small" type="warning" style="margin-right:6px">LC</el-tag>
                <el-tag v-else-if="mergePreviewData.payment_method === 'DA'" size="small" type="primary" style="margin-right:6px">DA</el-tag>
                <el-tag v-else-if="mergePreviewData.payment_method === 'DP'" size="small" type="info" style="margin-right:6px">DP</el-tag>
                <el-input v-model="mergePreviewData.payment_terms" size="small" clearable />
              </div>
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

        <!-- 产品明细表（树形可编辑） -->
        <div class="merge-toolbar" style="margin: 12px 0 8px; display: flex; gap: 8px; align-items: center;">
          <el-button size="small" type="primary" text @click="addMergeItem">
            <el-icon><Plus /></el-icon> 添加产品
          </el-button>
          <el-button
            size="small"
            type="warning"
            :disabled="selectedRows.filter(r => !r.isGroup).length < 2"
            @click="mergeSelected"
          >
            合并选中项
          </el-button>
          <span v-if="selectedRows.filter(r => !r.isGroup).length >= 2" style="font-size:12px;color:#909399">
            已选 {{ selectedRows.filter(r => !r.isGroup).length }} 个产品
          </span>
        </div>
        <el-table
          :data="treeData"
          row-key="rowUid"
          :tree-props="{ children: 'children' }"
          default-expand-all
          border stripe size="small"
          max-height="400"
          style="margin-top: 4px"
          @selection-change="onSelectionChange"
        >
          <el-table-column type="selection" width="40" :selectable="(row: MergeTableRow) => !row.isGroup" />
          <el-table-column label="内部编码/组名称" width="160">
            <template #default="{ row }">
              <template v-if="row.isGroup">
                <el-tag size="small" type="warning" style="margin-right:4px">组</el-tag>
                <el-input v-model="row.groupName" size="small" style="width:100px" @input="recalcGroup(row)" />
                <span style="color:#909399;font-size:12px;margin-left:4px">{{ row.children?.length || 0 }}项</span>
              </template>
              <el-input v-else v-model="row.internal_code" size="small" />
            </template>
          </el-table-column>
          <el-table-column prop="product_cn" label="产品名称" min-width="120">
            <template #default="{ row }">
              <span v-if="row.isGroup" style="color:#909399">—</span>
              <el-input v-else v-model="row.product_cn" size="small" />
            </template>
          </el-table-column>
          <el-table-column prop="spec_kg" label="规格kg" width="80" align="center">
            <template #default="{ row }">
              <span v-if="row.isGroup" style="color:#909399">—</span>
              <el-input-number v-else v-model="row.spec_kg" size="small" :controls="false" :precision="2" style="width:100%" />
            </template>
          </el-table-column>
          <el-table-column prop="quantity_kg" label="数量(kg)" width="100" align="center">
            <template #default="{ row }">
              <template v-if="row.isGroup">
                <span class="group-summary">{{ row.quantity_kg }}</span>
              </template>
              <el-input-number v-else v-model="row.quantity_kg" size="small" :controls="false" :precision="2" style="width:100%" @change="recalcGroupFromChild(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="unit_price" label="单价" width="90" align="center">
            <template #default="{ row }">
              <span v-if="row.isGroup" style="color:#909399">—</span>
              <el-input-number v-else v-model="row.unit_price" size="small" :controls="false" :precision="2" style="width:100%" @change="recalcGroupFromChild(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="total_amount" label="金额" width="100" align="center">
            <template #default="{ row }">
              <template v-if="row.isGroup">
                <span class="group-summary">{{ row.total_amount }}</span>
              </template>
              <el-input-number v-else v-model="row.total_amount" size="small" :controls="false" :precision="2" style="width:100%" @change="recalcGroupFromChild(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="hs_code" label="H.S.Code" width="120">
            <template #default="{ row }">
              <template v-if="row.isGroup && row.children && row.children.length > 0">
                <el-select v-model="row.hs_code" size="small" placeholder="选子项编码" style="width:100%">
                  <el-option
                    v-for="child in row.children"
                    :key="child.internal_code + (child.hs_code || '')"
                    :label="(child.hs_code || '') + ' · ' + (child.internal_code || '')"
                    :value="child.hs_code || ''"
                  />
                </el-select>
              </template>
              <el-input v-else v-model="row.hs_code" size="small" :class="{ 'is-warning': !row.hs_code }" />
            </template>
          </el-table-column>
          <el-table-column prop="customs_name" label="报关品名" min-width="130">
            <template #default="{ row }">
              <span v-if="row.isGroup" style="color:#909399">见子项</span>
              <el-input v-else v-model="row.customs_name" size="small" :class="{ 'is-warning': !row.customs_name }" />
            </template>
          </el-table-column>
          <el-table-column prop="customs_ingredients" label="报关成分" min-width="150">
            <template #default="{ row }">
              <span v-if="row.isGroup" style="color:#909399">见子项</span>
              <el-input v-else v-model="row.customs_ingredients" size="small" />
            </template>
          </el-table-column>
          <el-table-column prop="product_appearance" label="产品外观" min-width="100">
            <template #default="{ row }">
              <span v-if="row.isGroup" style="color:#909399">—</span>
              <el-input v-else v-model="row.product_appearance" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="70" fixed="right" align="center">
            <template #default="{ row }">
              <el-button v-if="row.isGroup" type="warning" text size="small" @click="ungroup(row)">
                解组
              </el-button>
              <el-button v-else type="danger" text size="small" @click="removeMergeItem(row)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>
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
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Delete, Plus } from '@element-plus/icons-vue'
import PasteTextarea from '@/components/phase1/PasteTextarea.vue'
import PiUploadDragger from '@/components/phase1/PiUploadDragger.vue'
import PackagingCalculator from '@/components/phase1/PackagingCalculator.vue'
import {
  ordersApi,
  type ParsedOrderSchema,
  type MergePreviewResponse,
  type MergePreviewItem,
  type LedgerWriteRequest,
} from '@/api/orders'
import { uploadPiFile, type PiUploadResponse } from '@/api/pi'
import { nameMappingApi } from '@/api/name_mapping'
import { generateUuid } from '@/utils/uid'

// ── 树形表行类型 ──────────────────────────────────────────────────────────────

interface MergeTableRow {
  rowUid: string
  isGroup: boolean
  groupName?: string
  groupId?: number
  children?: MergeTableRow[]
  // MergePreviewItem 字段
  internal_code: string
  product_cn?: string
  spec_kg?: number
  quantity_kg?: number
  unit_price?: number
  total_amount?: number
  hs_code?: string
  customs_name?: string
  customs_ingredients?: string
  product_appearance?: string
  source_pi_contract: boolean
  source_sales_order: boolean
  source_pi_file: boolean
  source_note?: string
  validation_status: string
  warnings: any[]
}

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

// 分组相关
const treeData = ref<MergeTableRow[]>([])
const selectedRows = ref<MergeTableRow[]>([])
let mergeGroupCounter = 1

// 保存
const saving = ref(false)
const savedRecordId = ref<number | null>(null)

// 包装计算
const calcRef = ref<InstanceType<typeof PackagingCalculator>>()
const showPackaging = ref(false)

// ── Computed ─────────────────────────────────────────────────────────────────

const canPreview = computed(() =>
  (piContractParsed.value && piContractOrders.value.length > 0) ||
  (salesOrderParsed.value && salesOrderOrders.value.length > 0)
)

const canSave = computed(() => mergePreviewData.value !== null)

// ── 树形数据同步 ──────────────────────────────────────────────────────────────

watch(() => mergePreviewData.value, (val) => {
  if (!val) {
    treeData.value = []
    return
  }
  treeData.value = val.items.map(item => ({
    rowUid: generateUuid(),
    isGroup: false,
    ...item,
  }))
}, { immediate: true })

// ── 分组操作 ──────────────────────────────────────────────────────────────────

function onSelectionChange(rows: MergeTableRow[]) {
  selectedRows.value = rows
}

function mergeSelected() {
  const selected = selectedRows.value
  if (selected.length < 2) {
    ElMessage.warning('请至少选择两个产品进行合并')
    return
  }
  // 检查选中的是否包含已分组的行
  const alreadyGrouped = selected.filter(r => !r.isGroup).some(r =>
    treeData.value.find(g => g.isGroup && g.children?.includes(r))
  )
  if (alreadyGrouped) {
    ElMessage.warning('选中的产品中有些已在分组中，请先解组')
    return
  }

  const groupId = -mergeGroupCounter++  // 使用负整数作为本地组ID
  const first = selected[0]
  const totalQty = selected.reduce((s, r) => s + (r.quantity_kg || 0), 0)
  const totalAmt = selected.reduce((s, r) => s + (r.total_amount || 0), 0)
  const calcPrice = totalQty > 0 ? Math.round((totalAmt / totalQty) * 100) / 100 : 0

  // 从 treeData 中移除选中的行
  const remaining = treeData.value.filter(r => !selected.includes(r))

  // 创建组头行
  const groupRow: MergeTableRow = {
    rowUid: generateUuid(),
    isGroup: true,
    groupName: `合并组 ${mergeGroupCounter - 1}`,
    groupId,
    children: [...selected],
    internal_code: '',
    product_cn: '',
    spec_kg: undefined,
    quantity_kg: totalQty,
    unit_price: calcPrice,
    total_amount: totalAmt,
    hs_code: first.hs_code || '',
    customs_name: first.customs_name || '',
    customs_ingredients: first.customs_ingredients || '',
    product_appearance: first.product_appearance || '',
    source_pi_contract: first.source_pi_contract,
    source_sales_order: first.source_sales_order,
    source_pi_file: first.source_pi_file,
    source_note: first.source_note,
    validation_status: first.validation_status,
    warnings: [],
  }

  // 将组头插入到第一个选中项的位置
  const firstIdx = treeData.value.indexOf(first)
  treeData.value = remaining
  treeData.value.splice(Math.max(0, firstIdx), 0, groupRow)
  selectedRows.value = []
}

function ungroup(row: MergeTableRow) {
  if (!row.isGroup || !row.children) return
  const idx = treeData.value.indexOf(row)
  if (idx === -1) return
  // 用子项替换组头
  treeData.value.splice(idx, 1, ...row.children)
}

function recalcGroup(row: MergeTableRow) {
  if (!row.isGroup || !row.children) return
  const totalQty = row.children.reduce((s, c) => s + (c.quantity_kg || 0), 0)
  const totalAmt = row.children.reduce((s, c) => s + (c.total_amount || 0), 0)
  row.quantity_kg = totalQty
  row.total_amount = totalAmt
  row.unit_price = totalQty > 0 ? Math.round((totalAmt / totalQty) * 100) / 100 : 0
}

function flattenTreeData(): any[] {
  const result: any[] = []
  for (const row of treeData.value) {
    if (row.isGroup && row.children) {
      // 组头行
      result.push({
        internal_code: '',  // 组头无内部编码
        product_cn: row.groupName || row.product_cn,
        spec_kg: undefined,
        quantity_kg: row.quantity_kg,
        unit_price: row.unit_price,
        total_amount: row.total_amount,
        hs_code: row.hs_code,
        customs_name: row.customs_name,
        customs_ingredients: undefined,
        product_appearance: undefined,
        source_pi_contract: row.source_pi_contract,
        source_sales_order: row.source_sales_order,
        source_pi_file: row.source_pi_file,
        source_note: row.source_note,
        validation_status: row.validation_status,
        warnings: row.warnings || [],
        // 分组字段通过额外属性传递
        _group_id: row.groupId,
        _group_name: row.groupName,
        _is_group_header: true,
      })

      // 子项行
      for (const child of row.children) {
        result.push({
          ...child,
          _group_id: row.groupId,
          _group_name: row.groupName,
          _is_group_header: false,
        })
      }
    } else if (!row.isGroup) {
      result.push(row)
    }
  }
  return result
}

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
    // 从树形数据展平，保留分组结构
    const flatItems = flattenTreeData()

    // 从计算器获取包装数据
    const calcSummary = calcRef.value?.getSummary()
    const calcRows = calcRef.value?.getRows() || []

    // 计算行按 内部编码 分组（保留顺序；同编码多行 = 拆行，如 3000 拆 1080+1080+840）
    const calcByCode: Record<string, any[]> = {}
    for (const row of calcRows) {
      const code = row.internal_code || row.product_name
      if (code) (calcByCode[code] = calcByCode[code] || []).push(row)
    }

    // 合并明细行按 内部编码 分组（非组头）
    const mergeItemsByCode: Record<string, any[]> = {}
    for (const item of flatItems) {
      const ext = item as any
      if (ext._is_group_header) continue
      if (item.internal_code) (mergeItemsByCode[item.internal_code] = mergeItemsByCode[item.internal_code] || []).push(item)
    }

    // 包装字段（从计算行取值）
    const packagingFields = (rowCalc: any) => ({
      packaging_name: rowCalc?.packaging_name || undefined,
      drum_count: rowCalc?.drums ?? undefined,
      pallet_count: rowCalc?.pallets ?? (rowCalc?.drums && rowCalc?.drums_per_pallet ? Math.ceil(rowCalc.drums / rowCalc.drums_per_pallet) : undefined),
      net_weight_kg: rowCalc?.net_weight_kg ?? undefined,
      gross_weight_kg: rowCalc?.gross_weight_kg ?? undefined,
      volume_cbm: rowCalc?.volume_cbm ?? undefined,
      fits_20gp: rowCalc?.fits_20gp || undefined,
      packaging_type_id: undefined,
      pallet_spec: rowCalc?.pallet_spec || undefined,
      drums_per_pallet: rowCalc?.drums_per_pallet ?? undefined,
    })

    const processedItems: any[] = []
    const consumedByCode: Record<string, number> = {}

    // 第一轮：按合并行顺序生成（组头占位 + 明细 1:1 配对；拆行编码本轮跳过）
    for (const item of flatItems) {
      const ext = item as any
      const isHeader = ext._is_group_header ?? false
      const groupId = ext._group_id

      if (isHeader) {
        processedItems.push({
          internal_code: `_group_${groupId ?? 0}`,
          product_cn: ext._group_name || item.product_cn,
          product_en: '',
          spec_kg: undefined,
          quantity_kg: item.quantity_kg,
          unit_price: item.unit_price,
          total_amount: item.total_amount,
          hs_code: item.hs_code,
          customs_name: item.customs_name,
          customs_ingredients: undefined,
          product_appearance: undefined,
          group_id: groupId ?? undefined,
          group_name: ext._group_name ?? undefined,
          is_group_header: true,
        })
        continue
      }

      const code = item.internal_code
      const calcLines = calcByCode[code] || []
      const mergeCount = mergeItemsByCode[code]?.length || 0
      if (calcLines.length > mergeCount && calcLines.length > 1) {
        // 拆行编码：本合并行是整单总量，具体行由第二轮按计算行统一生成
        continue
      }

      const idx = consumedByCode[code] || 0
      const rowCalc = calcLines[idx]
      consumedByCode[code] = idx + 1

      processedItems.push({
        internal_code: item.internal_code || `_group_${groupId ?? 0}`,
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
        group_id: groupId ?? undefined,
        group_name: ext._group_name ?? undefined,
        is_group_header: false,
        ...packagingFields(rowCalc),
      })
    }

    // 第二轮：拆行编码按计算行逐行生成（数量取各计算行，单价/品名取合并参考行）
    for (const [code, calcLines] of Object.entries(calcByCode)) {
      const refItems = mergeItemsByCode[code]
      if (!refItems || calcLines.length <= refItems.length) continue  // 已 1:1 配对
      const ref = refItems[0]
      for (const cRow of calcLines) {
        const qty = cRow.quantity_kg || 0
        const price = ref.unit_price ?? undefined
        processedItems.push({
          internal_code: code,
          product_cn: ref.product_cn || cRow.product_name,
          product_en: '',
          spec_kg: ref.spec_kg ?? undefined,
          quantity_kg: qty,
          unit_price: price,
          total_amount: qty && price ? Math.round(qty * price * 100) / 100 : undefined,
          hs_code: ref.hs_code,
          customs_name: ref.customs_name,
          customs_ingredients: ref.customs_ingredients,
          product_appearance: ref.product_appearance,
          group_id: (ref as any)._group_id ?? undefined,
          group_name: (ref as any)._group_name ?? undefined,
          is_group_header: false,
          ...packagingFields(cRow),
        })
      }
    }

    // 对组头行：从子项聚合包装数据（组头可能没有匹配包装计算，需要从子项累计）
    const childrenByGroup: Record<number, any[]> = {}
    for (const item of processedItems) {
      if (item.group_id != null && !item.is_group_header) {
        (childrenByGroup[item.group_id] = childrenByGroup[item.group_id] || []).push(item)
      }
    }
    for (const item of processedItems) {
      if (item.is_group_header && item.group_id != null) {
        const children = childrenByGroup[item.group_id] || []
        if (children.length > 0) {
          item.drum_count = children.reduce((s: number, c: any) => s + (c.drum_count || 0), 0)
          item.pallet_count = children.reduce((s: number, c: any) => s + (c.pallet_count || 0), 0)
          item.net_weight_kg = children.reduce((s: number, c: any) => s + (c.net_weight_kg || 0), 0)
          item.gross_weight_kg = children.reduce((s: number, c: any) => s + (c.gross_weight_kg || 0), 0)
          item.volume_cbm = children.reduce((s: number, c: any) => s + (c.volume_cbm || 0), 0)
        }
      }
    }

    // 校验：毛重/CBM 只来自包装计算器，产品未完成包装计算时不允许直接入库
    const nonHeaderItems = processedItems.filter(item => !item.is_group_header)
    if (nonHeaderItems.length === 0) {
      ElMessage.warning('没有可入库的产品，请先在合并预览中添加产品')
      return
    }
    const missingPackaging = nonHeaderItems
      .filter(item => !(item.drum_count > 0 && item.gross_weight_kg > 0 && item.volume_cbm > 0))
      .map(item => item.internal_code || item.product_cn || '未知产品')
    if (missingPackaging.length > 0) {
      try {
        await ElMessageBox.confirm(
          `以下 ${missingPackaging.length} 个产品未进行包装计算：<br><strong>${missingPackaging.join('、')}</strong><br><br>毛重/CBM 将不会生成。请先完成包装计算，或点「仍要入库」强制保存。`,
          '包装计算未完成',
          {
            confirmButtonText: '仍要入库',
            cancelButtonText: '去补算',
            type: 'warning',
            dangerouslyUseHTMLString: true,
          }
        )
      } catch {
        // 用户选择去补算：展开包装计算区（已有计算行则保留，否则自动预填产品）
        if (calcRef.value?.getRows().length) {
          showPackaging.value = true
        } else {
          handleShowPackaging()
        }
        return
      }
    }

    const items = processedItems

    // 查询英文名（跳过组头行）
    for (const item of items) {
      if (item.is_group_header) continue
      const cn = item.customs_name || item.product_cn || ''
      if (cn) {
        try {
          const res = await nameMappingApi.lookupByCn(cn)
          if (res.data.en) item.product_en = res.data.en
        } catch { /* ignore */ }
      }
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

    // 订单级重复检测：订单号已入台账 → 提示覆盖更新（同产品拆行属正常录入，不做产品级拦截）
    const existing = await ordersApi.getLedgerRecordByOrderNo(request.order_no)
    if (existing) {
      try {
        await ElMessageBox.confirm(
          `订单 ${request.order_no} 已录入台账（${existing.items?.length ?? 0} 条记录）。重复录入将覆盖更新该订单的全部记录，是否继续？`,
          '检测到重复订单',
          {
            confirmButtonText: '覆盖更新',
            cancelButtonText: '取消',
            type: 'warning',
          }
        )
      } catch {
        return
      }
      await doWriteLedger(request, true)
    } else {
      await doWriteLedger(request)
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '写入台账失败')
  } finally {
    saving.value = false
  }
}

async function doWriteLedger(request: LedgerWriteRequest, update = false) {
  saving.value = true
  try {
    const resp = update
      ? await ordersApi.updateLedger(request.order_no, request)
      : await ordersApi.writeLedger(request)
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

function calcRowAmount(row: any) {
  const qty = Number(row.quantity_kg) || 0
  const price = Number(row.unit_price) || 0
  row.total_amount = Math.round(qty * price * 100) / 100
}

function recalcGroupFromChild(row: MergeTableRow) {
  if (row.isGroup) return
  // 计算本行金额
  calcRowAmount(row)
  // 查找并更新父组
  for (const group of treeData.value) {
    if (group.isGroup && group.children?.includes(row)) {
      recalcGroup(group)
      break
    }
  }
}

async function handleShowPackaging() {
  showPackaging.value = true
  await nextTick()
  if (calcRef.value && treeData.value.length) {
    calcRef.value.clearRows()
    const flat = flattenTreeData()
    // 只添加子项（跳过组头行，组头数据从子项聚合）
    for (const item of flat) {
      if (item._is_group_header) continue
      calcRef.value.addRow(item.internal_code, item.product_cn || '', item.quantity_kg || 0)
    }
  }
}

function addMergeItem() {
  const newRow: MergeTableRow = {
    rowUid: generateUuid(),
    isGroup: false,
    internal_code: '',
    product_cn: '',
    spec_kg: undefined,
    quantity_kg: undefined,
    unit_price: undefined,
    total_amount: undefined,
    hs_code: '',
    customs_name: '',
    customs_ingredients: '',
    product_appearance: '',
    source_pi_contract: false,
    source_sales_order: false,
    source_pi_file: false,
    source_note: '',
    validation_status: 'ok',
    warnings: [],
  }
  treeData.value.push(newRow)
}

function removeMergeItem(row: MergeTableRow) {
  const idx = treeData.value.indexOf(row)
  if (idx !== -1) {
    treeData.value.splice(idx, 1)
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
  treeData.value = []
  selectedRows.value = []
  mergeGroupCounter = 1
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

/* 分组汇总值 */
.group-summary { font-weight: 600; color: #e6a23c; font-size: 13px; }

/* 包装区 */
.packaging-section { margin-top: 16px; }

/* 警告文字 */
.text-warning { color: #e6a23c; font-style: italic; }
.validation-warn { font-size: 13px; margin-top: 4px; }
</style>
