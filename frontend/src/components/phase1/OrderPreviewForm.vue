<template>
  <div class="order-preview-form">
    <!-- 批次重复警告 -->
    <el-alert
      v-if="parseResult.warning"
      :title="parseResult.warning"
      type="warning"
      show-icon
      :closable="true"
      style="margin-bottom: 16px"
    />

    <!-- 跳行提示 -->
    <el-alert
      v-if="parseResult.skipped_rows && parseResult.skipped_rows.length > 0"
      type="info"
      show-icon
      :closable="true"
      style="margin-bottom: 16px"
    >
      <template #title>
        {{ parseResult.skipped_rows.length }} 行因缺少必要字段被跳过（显示为灰色行）
      </template>
    </el-alert>

    <!-- 跳行灰色展示 -->
    <div v-if="parseResult.skipped_rows && parseResult.skipped_rows.length > 0" class="skipped-section">
      <el-table :data="parseResult.skipped_rows" border stripe size="small">
        <el-table-column type="index" label="行号" width="60" />
        <el-table-column prop="reason" label="跳过原因">
          <template #default="{ row }">
            <span style="color: #999">{{ row.reason }}</span>
          </template>
        </el-table-column>
        <el-table-column label="原始数据">
          <template #default="{ row }">
            <span style="color: #999; font-family: monospace; font-size: 12px">
              {{ row.raw_data.join(' | ') }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 订单卡片 -->
    <div v-for="order in parseResult.orders" :key="order.order_no" class="order-card">
      <!-- 订单头 -->
      <el-card shadow="never" class="order-header-card">
        <template #header>
          <div class="card-header">
            <span>订单号：{{ order.order_no }}</span>
            <el-tag v-if="order.header_conflict_warning" type="warning" size="small">
              有冲突字段
            </el-tag>
          </div>
        </template>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="客户编号">{{ order.customer_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="业务员">{{ order.salesperson || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="order.header_conflict_warning" class="conflict-warning">
          ⚠️ {{ order.header_conflict_warning }}
        </div>
      </el-card>

      <!-- 产品明细 -->
      <el-card shadow="never" class="items-card">
        <template #header>
          <div class="card-header">
            <span>产品明细（{{ order.items.length }} 条）</span>
            <el-checkbox
              v-model="allSelectedMap[order.order_no]"
              :indeterminate="isIndeterminate(order)"
              @change="(val: boolean) => toggleSelectAll(order, val)"
            >
              全选/反选
            </el-checkbox>
          </div>
        </template>

        <el-table
          :data="order.items"
          border
          stripe
          size="small"
          row-class-name="item-row"
        >
          <el-table-column type="index" width="50" />
          <el-table-column width="45">
            <template #default="{ row }">
              <el-checkbox
                v-model="row._selected"
                @change="() => updateIndeterminate(order)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="internal_code" label="内部编码" width="120" />
          <el-table-column prop="product_cn" label="产品中文名" min-width="160" />
          <el-table-column prop="spec_kg" label="规格kg" width="80" align="center" />
          <el-table-column prop="quantity_kg" label="订单量kg" width="100" align="right" />
          <el-table-column prop="unit_price" label="单价/kg" width="80" align="right" />
          <el-table-column prop="total_amount" label="总金额" width="100" align="right" />
          <el-table-column label="H.S.Code" width="180">
            <template #default="{ row }">
              <el-input
                v-model="row.hs_code"
                size="small"
                :class="{ 'is-warning': row.hs_code_warning || (row.hs_code && row.hs_code.length < 10) }"
                :placeholder="row.hs_code ? '' : '待填写'"
              />
              <span v-if="row.hs_code_warning || (row.hs_code && row.hs_code.length < 10)" class="field-warning">
                ⚠️ {{ row.hs_code_warning || '位数不足，请补足10位' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="报关品名" min-width="180">
            <template #default="{ row }">
              <el-input v-model="row.customs_name" size="small" />
              <span v-if="row.warning" class="field-warning">⚠️ {{ row.warning }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 操作按钮 -->
    <div class="form-actions">
      <el-button type="primary" @click="handleSave" :loading="saving">
        保存
      </el-button>
      <el-button @click="handleReset">
        重新粘贴
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import type { ParsedOrderSchema, PasteParseResponse } from '@/api/orders'

const props = defineProps<{
  parseResult: PasteParseResponse
}>()

const emit = defineEmits<{
  'save': [orders: ParsedOrderSchema[]]
  'reset': []
}>()

const saving = ref(false)

// 跟踪每个订单的全选状态
const allSelectedMap = reactive<Record<string, boolean>>({})

// 初始化全选状态
for (const order of props.parseResult.orders) {
  allSelectedMap[order.order_no] = true
  for (const item of order.items) {
    if (item._selected === undefined) item._selected = true
  }
}

function isIndeterminate(order: ParsedOrderSchema): boolean {
  const total = order.items.length
  const selected = order.items.filter(i => i._selected !== false).length
  return selected > 0 && selected < total
}

function toggleSelectAll(order: ParsedOrderSchema, selected: boolean) {
  for (const item of order.items) {
    item._selected = selected
  }
}

function updateIndeterminate(order: ParsedOrderSchema) {
  // 触发响应式更新
  allSelectedMap[order.order_no] = allSelectedMap[order.order_no]
}

async function handleSave() {
  saving.value = true
  try {
    // 只保存选中的订单（按订单聚合）
    const selectedOrders = props.parseResult.orders.filter(order =>
      order.items.some(item => item._selected !== false)
    ).map(order => ({
      ...order,
      items: order.items.filter(item => item._selected !== false)
    }))

    if (selectedOrders.length === 0) {
      return
    }

    emit('save', selectedOrders)
  } finally {
    saving.value = false
  }
}

function handleReset() {
  emit('reset')
}
</script>

<style scoped>
.order-preview-form {
  width: 100%;
}
.order-card {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.conflict-warning {
  margin-top: 8px;
  padding: 8px;
  background: #fffbe6;
  border-radius: 4px;
  font-size: 13px;
  color: #ad6800;
}
.field-warning {
  font-size: 12px;
  color: #ad6800;
  display: block;
  margin-top: 2px;
}
.is-warning :deep(.el-input__inner) {
  border-color: #faad14 !important;
  background: #fffbe6;
}
.form-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
.skipped-section {
  margin-bottom: 16px;
}
</style>