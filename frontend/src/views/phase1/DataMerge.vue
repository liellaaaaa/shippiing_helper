<template>
  <div class="data-merge-page">
    <!-- 顶部：Tab + 搜索 -->
    <div class="filter-bar">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="🔴 待处理" name="pending" />
        <el-tab-pane label="🟢 已完成" name="completed" />
        <el-tab-pane label="📋 全部" name="all" />
      </el-tabs>
      <el-input
        v-model="searchText"
        placeholder="搜索订单号 / 内部编码 / 客户名称"
        clearable
        class="search-input"
        @keyup.enter="handleSearch"
      >
        <template #append>
          <el-button icon="Search" @click="handleSearch" />
        </template>
      </el-input>
    </div>

    <!-- 订单列表：可展开表格 -->
    <el-table
      :data="orderList"
      border
      stripe
      v-loading="loading"
      row-key="id"
      :expand-row-keys="expandedRows"
      class="order-table"
    >
      <el-table-column type="expand" width="50">
        <template #default="{ row }">
          <OrderExpandRow
            v-if="expandedRows.includes(row.id)"
            :order-id="row.id"
          />
        </template>
      </el-table-column>

      <el-table-column prop="order_no" label="订单号" width="160" />
      <el-table-column prop="customer_code" label="客户编码" width="140" />
      <el-table-column prop="salesperson" label="业务员" width="100" />
      <el-table-column prop="total_amount" label="订单总金额" width="120" align="right">
        <template #default="{ row }">
          {{ row.total_amount ? `¥${row.total_amount.toLocaleString()}` : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="items_count" label="产品数" width="80" align="center" />
      <el-table-column label="关联状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.association_status)">
            {{ statusLabel(row.association_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建日期" width="120" />
      <el-table-column label="操作" width="80" align="center">
        <template #default="{ row }">
          <el-button
            link
            type="primary"
            @click="toggleExpand(row.id)"
          >
            {{ expandedRows.includes(row.id) ? '收起' : '查看' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getOrderList, type OrderListItem } from '@/api/merge'
import OrderExpandRow from '@/components/phase1/OrderExpandRow.vue'

const activeTab = ref('pending')
const searchText = ref('')
const orderList = ref<OrderListItem[]>([])
const loading = ref(false)
const expandedRows = ref<number[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const statusType = (status: string) => {
  if (status === 'full') return 'success'
  if (status === 'partial') return 'warning'
  return 'danger'
}

const statusLabel = (status: string) => {
  if (status === 'full') return '已关联'
  if (status === 'partial') return '部分关联'
  return '未关联'
}

const loadData = async () => {
  loading.value = true
  try {
    const response = await getOrderList({
      tab: activeTab.value,
      search: searchText.value || undefined,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    orderList.value = response.orders
    total.value = response.total
  } catch (error) {
    console.error('Failed to load order list:', error)
  } finally {
    loading.value = false
  }
}

const handleTabChange = () => {
  currentPage.value = 1
  expandedRows.value = []
  loadData()
}

const handleSearch = () => {
  currentPage.value = 1
  loadData()
}

const toggleExpand = (id: number) => {
  const idx = expandedRows.value.indexOf(id)
  if (idx >= 0) {
    expandedRows.value.splice(idx, 1)
  } else {
    expandedRows.value.push(id)
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.data-merge-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: #909399; margin: 0; }
.filter-bar { display: flex; gap: 16px; align-items: center; margin-bottom: 20px; }
.filter-bar .el-tabs { flex: 0 0 auto; }
.search-input { width: 320px; }
.order-table { margin-bottom: 16px; }
.pagination-wrapper { display: flex; justify-content: flex-end; }
</style>