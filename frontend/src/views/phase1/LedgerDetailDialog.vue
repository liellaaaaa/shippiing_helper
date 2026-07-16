<template>
  <el-dialog
    v-model="visible"
    :title="isEditing ? '台账编辑' : '台账详情'"
    width="min(calc(100% - 48px), 1352px)"
    top="24px"
    class="ledger-dialog"
    destroy-on-close
    @close="handleClose"
  >
    <div v-if="record" class="ledger-detail">
      <el-tabs v-model="activeTab">
        <!-- Tab 1: 订单信息 -->
        <el-tab-pane label="订单信息" name="order">
          <div class="info-sections">
            <!-- PI 合同表数据 -->
            <el-divider content-position="left">PI 合同表数据</el-divider>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="订单号/PI号">
                <template v-if="isEditing"><el-input v-model="editData.order_no" size="small" /></template>
                <template v-else>{{ record.order_no || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="客户编码">
                <template v-if="isEditing"><el-input v-model="editData.customer_code" size="small" /></template>
                <template v-else>{{ record.customer_code || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="业务员">
                <template v-if="isEditing"><el-input v-model="editData.sales_person" size="small" /></template>
                <template v-else>{{ record.sales_person || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="PI号">
                <template v-if="isEditing"><el-input v-model="editData.pi_no" size="small" /></template>
                <template v-else>{{ record.pi_no || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="PI日期">
                <template v-if="isEditing"><el-input v-model="editData.pi_date" size="small" /></template>
                <template v-else>{{ record.pi_date || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="record.status === 'editing' ? 'warning' : 'info'">
                  {{ record.status || 'pending' }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>

            <!-- 销售订单表数据 -->
            <el-divider content-position="left">销售订单表数据</el-divider>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="销售订单号">
                <template v-if="isEditing"><el-input v-model="editData.sales_order_no" size="small" /></template>
                <template v-else>{{ record.sales_order_no || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="跟单员">
                <template v-if="isEditing"><el-input v-model="editData.merchandiser" size="small" /></template>
                <template v-else>{{ record.merchandiser || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="出货抬头">
                <template v-if="isEditing"><el-input v-model="editData.shipment_title" size="small" /></template>
                <template v-else>{{ record.shipment_title || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="下单日期">
                <template v-if="isEditing"><el-input v-model="editData.order_date" size="small" /></template>
                <template v-else>{{ record.order_date || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="交货日期">
                <template v-if="isEditing"><el-input v-model="editData.delivery_date" size="small" /></template>
                <template v-else>{{ record.delivery_date || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="生产交期">
                <template v-if="isEditing"><el-input v-model="editData.production_deadline" size="small" /></template>
                <template v-else>{{ record.production_deadline || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="出货渠道">
                <template v-if="isEditing"><el-input v-model="editData.shipment_channel" size="small" /></template>
                <template v-else>{{ record.shipment_channel || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="出货方式">
                <template v-if="isEditing"><el-input v-model="editData.shipment_method" size="small" /></template>
                <template v-else>{{ record.shipment_method || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="单据类型">
                <template v-if="isEditing"><el-input v-model="editData.document_type" size="small" /></template>
                <template v-else>{{ record.document_type || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="审核状态">
                <template v-if="isEditing"><el-input v-model="editData.review_status" size="small" /></template>
                <template v-else>{{ record.review_status || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="规格异常">
                <template v-if="isEditing"><el-input v-model="editData.spec_abnormal" size="small" /></template>
                <template v-else>{{ record.spec_abnormal || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="有无样品">
                <template v-if="isEditing"><el-input v-model="editData.has_sample" size="small" /></template>
                <template v-else>{{ record.has_sample || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="是否调价">
                <template v-if="isEditing"><el-input v-model="editData.price_adjusted" size="small" /></template>
                <template v-else>{{ record.price_adjusted || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="确认下单">
                <template v-if="isEditing"><el-input v-model="editData.order_confirmed" size="small" /></template>
                <template v-else>{{ record.order_confirmed || '-' }}</template>
              </el-descriptions-item>
            </el-descriptions>

            <!-- PI 合同文件数据 -->
            <el-divider content-position="left">PI 合同文件数据</el-divider>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="收货人名称" :span="2">
                <template v-if="isEditing"><el-input v-model="editData.consignee_name" size="small" /></template>
                <template v-else>{{ record.consignee_name || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="电话">
                <template v-if="isEditing"><el-input v-model="editData.consignee_tel" size="small" /></template>
                <template v-else>{{ record.consignee_tel || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="收货人地址" :span="3">
                <template v-if="isEditing"><el-input v-model="editData.consignee_address" size="small" /></template>
                <template v-else>{{ record.consignee_address || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="目的港">
                <template v-if="isEditing"><el-input v-model="editData.destination" size="small" /></template>
                <template v-else>{{ record.destination || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="装货港">
                <template v-if="isEditing"><el-input v-model="editData.loading_port" size="small" /></template>
                <template v-else>{{ record.loading_port || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="价格条款">
                <template v-if="isEditing"><el-input v-model="editData.price_term" size="small" /></template>
                <template v-else>{{ record.price_term || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="币制">
                <template v-if="isEditing"><el-input v-model="editData.currency" size="small" /></template>
                <template v-else>{{ record.currency || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="付款方式" :span="2">
                <template v-if="isEditing"><el-input v-model="editData.payment_terms" size="small" /></template>
                <template v-else>{{ record.payment_terms || '-' }}</template>
              </el-descriptions-item>
              <el-descriptions-item label="银行信息" :span="3">
                <template v-if="isEditing"><el-input v-model="editData.bank_info" size="small" /></template>
                <template v-else>{{ record.bank_info || '-' }}</template>
              </el-descriptions-item>
            </el-descriptions>

            <!-- 录入时间 -->
            <el-divider content-position="left">系统信息</el-divider>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="录入时间">{{ record.created_at ? formatDate(record.created_at) : '-' }}</el-descriptions-item>
              <el-descriptions-item label="产品数">
                <el-tag type="info">{{ editData.items?.length || 0 }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-tab-pane>

        <!-- Tab 2: 产品明细 -->
        <el-tab-pane label="产品明细" name="products">
          <div v-if="isEditing" class="product-toolbar">
            <el-button type="primary" size="small" icon="Plus" @click="addProductRow">添加产品</el-button>
          </div>
          <el-table
            :data="editData.items || []"
            border
            class="product-table"
          >
            <el-table-column v-if="isEditing" label="" width="50" fixed align="center">
              <template #default="{ $index }">
                <el-button type="danger" link @click="removeProductRow($index)">
                  <span style="font-size: 20px; font-weight: bold;">×</span>
                </el-button>
              </template>
            </el-table-column>
            <el-table-column prop="internal_code" label="内部编码" width="120" fixed>
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model="row.internal_code" size="small" /></template>
                <template v-else>{{ row.internal_code || '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="product_cn" label="产品名称" min-width="130" show-overflow-tooltip>
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model="row.product_cn" size="small" /></template>
                <template v-else>{{ row.product_cn || '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="product_en" label="英文名" min-width="130" show-overflow-tooltip>
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model="row.product_en" size="small" /></template>
                <template v-else>{{ row.product_en || '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="spec_kg" label="规格kg" width="90" align="right" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model.number="row.spec_kg" size="small" type="number" /></template>
                <template v-else>{{ row.spec_kg ?? '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="quantity_kg" label="数量kg" width="110" align="right" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model.number="row.quantity_kg" size="small" type="number" /></template>
                <template v-else>{{ row.quantity_kg ?? '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="unit_price" label="单价" width="90" align="right" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model.number="row.unit_price" size="small" type="number" /></template>
                <template v-else>{{ row.unit_price != null ? row.unit_price.toFixed(2) : '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="total_amount" label="金额" width="110" align="right" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model.number="row.total_amount" size="small" type="number" /></template>
                <template v-else>{{ row.total_amount != null ? row.total_amount.toFixed(2) : '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="hs_code" label="H.S.Code" width="120">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model="row.hs_code" size="small" /></template>
                <template v-else>{{ row.hs_code || '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="customs_name" label="报关品名" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model="row.customs_name" size="small" /></template>
                <template v-else>{{ row.customs_name || '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="customs_ingredients" label="报关成分" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model="row.customs_ingredients" size="small" /></template>
                <template v-else>{{ row.customs_ingredients || '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="product_appearance" label="产品外观" min-width="110" show-overflow-tooltip>
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model="row.product_appearance" size="small" /></template>
                <template v-else>{{ row.product_appearance || '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="packaging_type_id" label="包装类型" width="90" align="center" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model.number="row.packaging_type_id" size="small" type="number" /></template>
                <template v-else>{{ row.packaging_type_id ?? '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="pallet_spec" label="托盘规格" width="90">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model="row.pallet_spec" size="small" /></template>
                <template v-else>{{ row.pallet_spec || '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="drums_per_pallet" label="每托桶数" width="90" align="center" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model.number="row.drums_per_pallet" size="small" type="number" /></template>
                <template v-else>{{ row.drums_per_pallet ?? '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="drum_count" label="总桶数" width="80" align="center" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model.number="row.drum_count" size="small" type="number" /></template>
                <template v-else>{{ row.drum_count ?? '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="pallet_count" label="总托数" width="80" align="center" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model.number="row.pallet_count" size="small" type="number" /></template>
                <template v-else>{{ row.pallet_count ?? '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="net_weight_kg" label="净重kg" width="100" align="right" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model.number="row.net_weight_kg" size="small" type="number" /></template>
                <template v-else>{{ row.net_weight_kg ?? '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="gross_weight_kg" label="毛重kg" width="100" align="right" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model.number="row.gross_weight_kg" size="small" type="number" /></template>
                <template v-else>{{ row.gross_weight_kg ?? '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="volume_cbm" label="体积CBM" width="100" align="right" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model.number="row.volume_cbm" size="small" type="number" /></template>
                <template v-else>{{ row.volume_cbm ?? '-' }}</template>
              </template>
            </el-table-column>
            <el-table-column prop="fits_20gp" label="20GP适配" width="100" align="center" header-align="left">
              <template #default="{ row }">
                <template v-if="isEditing"><el-input v-model="row.fits_20gp" size="small" /></template>
                <template v-else>{{ row.fits_20gp || '-' }}</template>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <template v-if="!isEditing">
          <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
          <el-button @click="enterEdit">编辑</el-button>
          <el-button type="primary" @click="record && $emit('edit', record)">
            进入文档编辑
          </el-button>
        </template>
        <template v-else>
          <el-button @click="cancelEdit">取消编辑</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">
            修改完毕
          </el-button>
        </template>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ordersApi, type LedgerRecord, type LedgerItem } from '@/api/orders'

const props = defineProps<{
  modelValue: boolean
  record: LedgerRecord | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'edit': [record: LedgerRecord]
  'saved': []
}>()

const visible = ref(props.modelValue)
const activeTab = ref('order')
const isEditing = ref(false)
const saving = ref(false)

const editData = ref({
  order_no: '',
  customer_code: '',
  sales_person: '',
  pi_no: '',
  pi_date: '',
  sales_order_no: '',
  merchandiser: '',
  order_date: '',
  delivery_date: '',
  shipment_channel: '',
  shipment_method: '',
  document_type: '',
  review_status: '',
  spec_abnormal: '',
  has_sample: '',
  price_adjusted: '',
  order_confirmed: '',
  production_deadline: '',
  shipment_title: '',
  consignee_name: '',
  consignee_tel: '',
  consignee_address: '',
  destination: '',
  loading_port: '',
  price_term: '',
  currency: '',
  payment_terms: '',
  bank_info: '',
  items: [] as LedgerItem[],
})

function cloneRecord(r: LedgerRecord) {
  return {
    order_no: r.order_no || '',
    customer_code: r.customer_code || '',
    sales_person: r.sales_person || '',
    pi_no: r.pi_no || '',
    pi_date: r.pi_date || '',
    sales_order_no: r.sales_order_no || '',
    merchandiser: r.merchandiser || '',
    order_date: r.order_date || '',
    delivery_date: r.delivery_date || '',
    shipment_channel: r.shipment_channel || '',
    shipment_method: r.shipment_method || '',
    document_type: r.document_type || '',
    review_status: r.review_status || '',
    spec_abnormal: r.spec_abnormal || '',
    has_sample: r.has_sample || '',
    price_adjusted: r.price_adjusted || '',
    order_confirmed: r.order_confirmed || '',
    production_deadline: r.production_deadline || '',
    shipment_title: r.shipment_title || '',
    consignee_name: r.consignee_name || '',
    consignee_tel: r.consignee_tel || '',
    consignee_address: r.consignee_address || '',
    destination: r.destination || '',
    loading_port: r.loading_port || '',
    price_term: r.price_term || '',
    currency: r.currency || '',
    payment_terms: r.payment_terms || '',
    bank_info: r.bank_info || '',
    items: (r.items || []).map((item) => ({ ...item })),
  }
}

watch(() => props.modelValue, (val) => { visible.value = val })
watch(visible, (val) => {
  if (!val) {
    activeTab.value = 'order'
    isEditing.value = false
  }
})
watch(() => props.record, (r) => {
  if (r) editData.value = cloneRecord(r)
}, { immediate: true })

function enterEdit() {
  if (props.record) {
    editData.value = cloneRecord(props.record)
  }
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
}

function handleClose() {
  isEditing.value = false
  emit('update:modelValue', false)
}

function addProductRow() {
  editData.value.items.push({
    internal_code: '',
    product_cn: '',
    product_en: '',
    spec_kg: undefined,
    quantity_kg: undefined,
    unit_price: undefined,
    total_amount: undefined,
    hs_code: '',
    customs_name: '',
    customs_ingredients: '',
    product_appearance: '',
    packaging_type_id: undefined,
    pallet_spec: '',
    drums_per_pallet: undefined,
    drum_count: undefined,
    pallet_count: undefined,
    net_weight_kg: undefined,
    gross_weight_kg: undefined,
    volume_cbm: undefined,
    fits_20gp: '',
  })
}

function removeProductRow(index: number) {
  editData.value.items.splice(index, 1)
}

async function handleSave() {
  if (!props.record) return
  saving.value = true
  try {
    const { pi_no: _, ...payload } = editData.value
    await ordersApi.updateLedger(editData.value.order_no, payload as any)
    ElMessage.success('台账已更新')
    isEditing.value = false
    emit('saved')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
  } catch {
    return dateStr
  }
}
</script>

<style scoped>
.ledger-detail { padding: 0 8px; }
.info-sections { display: flex; flex-direction: column; gap: 4px; }
.info-sections .el-divider { margin: 16px 0 8px; }
.product-table { width: 100%; }
.dialog-footer { display: flex; justify-content: flex-end; gap: 8px; }
.product-toolbar { margin-bottom: 8px; }
</style>

<style>
/* 弹窗撑满视口高度 */
.ledger-dialog .el-dialog {
  height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
  margin-bottom: 24px;
}
.ledger-dialog .el-dialog__body {
  flex: 1;
  overflow-y: auto;
  padding-top: 8px;
}
/* 弹窗内表格字号与页面一致 */
.ledger-dialog .el-table {
  font-size: 14px;
}
.ledger-dialog .el-table .el-table__header th {
  font-size: 14px;
}
.ledger-dialog .el-table .el-table__body td {
  font-size: 14px;
}
/* 弹窗内描述列表统一样式 */
.ledger-dialog .el-descriptions__label {
  font-size: 14px;
  width: 100px;
  text-align: left;
}
.ledger-dialog .el-descriptions__content {
  font-size: 14px;
  text-align: left;
}
.ledger-dialog .el-divider__text {
  font-size: 14px;
}
</style>
