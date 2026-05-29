<template>
  <div class="expand-row" v-loading="loading">
    <table class="comparison-table" v-if="!loading && comparison">
      <thead>
        <tr>
          <th>内部编码</th>
          <th>产品名称</th>
          <th>📦 订单数量/单价</th>
          <th>📄 PI 数量/单价</th>
          <th>差异状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in comparison.items" :key="item.internal_code">
          <td>{{ item.internal_code }}</td>
          <td>{{ item.product_cn || '-' }}</td>
          <td>
            <div class="cell-value">
              <span>{{ item.order?.quantity ?? '-' }} kg</span>
              <span class="secondary">{{ item.order?.unit_price ? `¥${item.order.unit_price}` : '' }}</span>
            </div>
          </td>
          <td>
            <div class="cell-value" :class="{ 'pi-missing': !item.pi }">
              <span v-if="item.pi">{{ item.pi.quantity ?? '-' }} kg</span>
              <span v-else class="no-data">— 无 PI 记录</span>
              <span v-if="item.pi?.unit_price" class="secondary">¥{{ item.pi.unit_price }}</span>
            </div>
          </td>
          <td>
            <DiffCell
              :order-value="item.order?.quantity"
              :pi-value="item.pi?.quantity"
              :diff-status="item.diff.status"
              :flags="item.diff.flags"
            />
          </td>
          <td>
            <QuickJumpPopover
              :internal-code="item.internal_code"
              :order-id="orderId"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getOrderComparison, type OrderComparisonResponse } from '@/api/merge'
import DiffCell from './DiffCell.vue'
import QuickJumpPopover from './QuickJumpPopover.vue'

const props = defineProps<{
  orderId: number
}>()

const loading = ref(false)
const comparison = ref<OrderComparisonResponse | null>(null)

const loadComparison = async () => {
  loading.value = true
  try {
    comparison.value = await getOrderComparison(props.orderId)
  } catch (error) {
    console.error('Failed to load comparison:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadComparison()
})
</script>

<style scoped>
.expand-row { padding: 12px 20px; background: #f5f7fa; }
.comparison-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.comparison-table th { text-align: left; padding: 8px 12px; background: #e4e7ed; border: 1px solid #dcdfe6; }
.comparison-table td { padding: 8px 12px; border: 1px solid #dcdfe6; background: #fff; }
.cell-value { display: flex; flex-direction: column; }
.cell-value .secondary { color: #909399; font-size: 12px; }
.no-data { color: #c0c4cc; font-style: italic; }
</style>