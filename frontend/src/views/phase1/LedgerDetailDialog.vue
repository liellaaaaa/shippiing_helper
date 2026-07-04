<template>
  <el-dialog
    v-model="visible"
    title="台账详情"
    width="min(calc(100% - 48px), 1352px)"
    top="24px"
    class="ledger-dialog"
    destroy-on-close
    @close="$emit('update:modelValue', false)"
  >
    <div v-if="record" class="ledger-detail">
      <el-tabs v-model="activeTab">
        <!-- Tab 1: 订单信息 -->
        <el-tab-pane label="订单信息" name="order">
          <div class="info-sections">
            <!-- PI 合同表数据 -->
            <el-divider content-position="left">PI 合同表数据</el-divider>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="订单号/PI号">{{ record.order_no || '-' }}</el-descriptions-item>
              <el-descriptions-item label="客户编码">{{ record.customer_code || '-' }}</el-descriptions-item>
              <el-descriptions-item label="业务员">{{ record.sales_person || '-' }}</el-descriptions-item>
              <el-descriptions-item label="PI号">{{ record.pi_no || '-' }}</el-descriptions-item>
              <el-descriptions-item label="PI日期">{{ record.pi_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="record.status === 'editing' ? 'warning' : 'info'">
                  {{ record.status || 'pending' }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>

            <!-- 销售订单表数据 -->
            <el-divider content-position="left">销售订单表数据</el-divider>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="销售订单号">{{ record.sales_order_no || '-' }}</el-descriptions-item>
              <el-descriptions-item label="跟单员">{{ record.merchandiser || '-' }}</el-descriptions-item>
              <el-descriptions-item label="出货抬头">{{ record.shipment_title || '-' }}</el-descriptions-item>
              <el-descriptions-item label="下单日期">{{ record.order_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="交货日期">{{ record.delivery_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="生产交期">{{ record.production_deadline || '-' }}</el-descriptions-item>
              <el-descriptions-item label="出货渠道">{{ record.shipment_channel || '-' }}</el-descriptions-item>
              <el-descriptions-item label="出货方式">{{ record.shipment_method || '-' }}</el-descriptions-item>
              <el-descriptions-item label="单据类型">{{ record.document_type || '-' }}</el-descriptions-item>
              <el-descriptions-item label="审核状态">{{ record.review_status || '-' }}</el-descriptions-item>
              <el-descriptions-item label="规格异常">{{ record.spec_abnormal || '-' }}</el-descriptions-item>
              <el-descriptions-item label="有无样品">{{ record.has_sample || '-' }}</el-descriptions-item>
              <el-descriptions-item label="是否调价">{{ record.price_adjusted || '-' }}</el-descriptions-item>
              <el-descriptions-item label="确认下单">{{ record.order_confirmed || '-' }}</el-descriptions-item>
            </el-descriptions>

            <!-- PI 合同文件数据 -->
            <el-divider content-position="left">PI 合同文件数据</el-divider>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="收货人名称" :span="2">{{ record.consignee_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="电话">{{ record.consignee_tel || '-' }}</el-descriptions-item>
              <el-descriptions-item label="收货人地址" :span="3">{{ record.consignee_address || '-' }}</el-descriptions-item>
              <el-descriptions-item label="目的港">{{ record.destination || '-' }}</el-descriptions-item>
              <el-descriptions-item label="装货港">{{ record.loading_port || '-' }}</el-descriptions-item>
              <el-descriptions-item label="价格条款">{{ record.price_term || '-' }}</el-descriptions-item>
              <el-descriptions-item label="付款方式" :span="2">{{ record.payment_terms || '-' }}</el-descriptions-item>
              <el-descriptions-item label="银行信息" :span="3">{{ record.bank_info || '-' }}</el-descriptions-item>
            </el-descriptions>

            <!-- 录入时间 -->
            <el-divider content-position="left">系统信息</el-divider>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="录入时间">{{ record.created_at ? formatDate(record.created_at) : '-' }}</el-descriptions-item>
              <el-descriptions-item label="产品数">
                <el-tag type="info">{{ record.items?.length || 0 }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-tab-pane>

        <!-- Tab 2: 产品明细 -->
        <el-tab-pane label="产品明细" name="products">
          <el-table
            :data="record.items || []"
            border
            class="product-table"
          >
            <el-table-column prop="internal_code" label="内部编码" width="120" fixed />
            <el-table-column prop="product_cn" label="产品名称" min-width="130" show-overflow-tooltip />
            <el-table-column prop="product_en" label="英文名" min-width="130" show-overflow-tooltip />
            <el-table-column prop="spec_kg" label="规格kg" width="90" align="right" />
            <el-table-column prop="quantity_kg" label="数量kg" width="110" align="right" />
            <el-table-column prop="unit_price" label="单价" width="90" align="right">
              <template #default="{ row }">
                {{ row.unit_price != null ? row.unit_price.toFixed(2) : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="total_amount" label="金额" width="110" align="right">
              <template #default="{ row }">
                {{ row.total_amount != null ? row.total_amount.toFixed(2) : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="hs_code" label="H.S.Code" width="120" />
            <el-table-column prop="customs_name" label="报关品名" min-width="150" show-overflow-tooltip />
            <el-table-column prop="customs_ingredients" label="报关成分" min-width="150" show-overflow-tooltip />
            <el-table-column prop="product_appearance" label="产品外观" min-width="110" show-overflow-tooltip />
            <el-table-column prop="packaging_type_id" label="包装类型" width="90" align="center" />
            <el-table-column prop="pallet_spec" label="托盘规格" width="90" />
            <el-table-column prop="drums_per_pallet" label="每托桶数" width="90" align="center" />
            <el-table-column prop="drum_count" label="总桶数" width="80" align="center" />
            <el-table-column prop="pallet_count" label="总托数" width="80" align="center" />
            <el-table-column prop="net_weight_kg" label="净重kg" width="100" align="right" />
            <el-table-column prop="gross_weight_kg" label="毛重kg" width="100" align="right" />
            <el-table-column prop="volume_cbm" label="体积CBM" width="100" align="right" />
            <el-table-column prop="fits_20gp" label="20GP适配" width="100" align="center" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
        <el-button type="primary" @click="record && $emit('edit', record)">
          进入文档编辑
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { LedgerRecord } from '@/api/orders'

const props = defineProps<{
  modelValue: boolean
  record: LedgerRecord | null
}>()

defineEmits<{
  'update:modelValue': [value: boolean]
  'edit': [record: LedgerRecord]
}>()

const visible = ref(props.modelValue)
const activeTab = ref('order')

watch(() => props.modelValue, (val) => { visible.value = val })
watch(visible, (val) => { if (!val) activeTab.value = 'order' })

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
/* 弹窗内描述列表字号与页面一致 */
.ledger-dialog .el-descriptions__label,
.ledger-dialog .el-descriptions__content {
  font-size: 14px;
}
.ledger-dialog .el-divider__text {
  font-size: 14px;
}
</style>
