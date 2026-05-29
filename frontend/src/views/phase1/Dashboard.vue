<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1 class="page-title">数据看板</h1>
      <p class="page-subtitle">订单与 PI 合并数据汇总 — 确认数据无误后进入文档编辑</p>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchText"
          placeholder="搜索订单号 / 客户编码"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button icon="Search" @click="handleSearch" />
          </template>
        </el-input>

        <el-select
          v-model="selectedStatuses"
          multiple
          placeholder="关联状态筛选"
          collapse-tags
          collapse-tags-tooltip
          class="status-filter"
        >
          <el-option
            v-for="s in statusOptions"
            :key="s.value"
            :label="s.label"
            :value="s.value"
          />
        </el-select>
      </div>

      <div class="toolbar-right">
        <el-button type="primary" icon="Download" @click="handleExportExcel">
          导出 Excel
        </el-button>
        <el-button plain icon="Printer" @click="handlePrintPreview">
          打印预览
        </el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-table
      :data="orderList"
      border
      stripe
      v-loading="loading"
      row-key="order_id"
      class="data-table"
    >
      <el-table-column prop="order_no" label="订单号" width="140" fixed />
      <el-table-column prop="customer_code" label="客户编码" width="120" />
      <el-table-column prop="salesperson" label="业务员" width="100" />
      <el-table-column prop="internal_code" label="内部编码" width="120" />
      <el-table-column prop="product_cn" label="产品名称" width="160" />
      <el-table-column prop="order_quantity" label="订单数量" width="100" align="right">
        <template #default="{ row }">
          {{ row.order_quantity ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="pi_quantity" label="PI 数量" width="100" align="right">
        <template #default="{ row }">
          {{ row.pi_quantity ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="diff_status" label="差异状态" width="120">
        <template #default="{ row }">
          <el-tag :type="diffStatusType(row.diff_status)" size="small">
            {{ row.diff_status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="association_status" label="关联状态" width="100">
        <template #default="{ row }">
          <el-tooltip :content="getStatusTip(row.association_status)" placement="top">
            <el-tag :type="statusType(row.association_status)" size="small">
              {{ statusLabel(row.association_status) }}
            </el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper no-print">
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
import { ref, onMounted, watch } from 'vue'
import { getDashboardOrders, exportDashboardExcel, type DashboardOrder } from '@/api/dashboard'

const searchText = ref('')
const selectedStatuses = ref<string[]>([])
const orderList = ref<DashboardOrder[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(50)
const total = ref(0)

const statusOptions = [
  { label: '已关联', value: 'full' },
  { label: '部分关联', value: 'partial' },
  { label: '未关联', value: 'none' },
]

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

const getStatusTip = (status: string) => {
  if (status === 'none') return '此订单没有任何产品匹配 PI，需要补充 PI 数据'
  if (status === 'partial') return '此订单部分产品未匹配 PI 或存在数据差异'
  return '此订单所有产品均已匹配 PI，数据一致'
}

const diffStatusType = (status: string) => {
  if (status === '一致') return 'success'
  if (status === 'PI未覆盖') return 'warning'
  return 'danger'
}

const buildStatusParam = () => {
  if (selectedStatuses.value.length === 0) return undefined
  return selectedStatuses.value.join(",")
}

const loadData = async () => {
  loading.value = true
  try {
    const response = await getDashboardOrders({
      search: searchText.value || undefined,
      status: buildStatusParam(),
      page: currentPage.value,
      page_size: pageSize.value,
    })
    orderList.value = response.orders
    total.value = response.total
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadData()
}

watch(selectedStatuses, () => {
  currentPage.value = 1
  loadData()
})

const handleExportExcel = () => {
  const params: any = {}
  if (searchText.value) params.search = searchText.value
  if (buildStatusParam()) params.status = buildStatusParam()
  exportDashboardExcel(params)
}

const handlePrintPreview = () => {
  window.print()
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: #909399; margin: 0; }

.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding: 12px 16px; background: #f5f7fa; border-radius: 8px; }
.toolbar-left { display: flex; gap: 12px; align-items: center; }
.toolbar-right { display: flex; gap: 8px; }
.search-input { width: 240px; }
.status-filter { width: 180px; }

.data-table { margin-bottom: 16px; }

.pagination-wrapper { display: flex; justify-content: flex-end; }

/* 打印样式 */
@media print {
  .toolbar { display: none !important; }
  .no-print { display: none !important; }
  .page-header { margin-bottom: 12px; }
  .page-title { font-size: 20px; }
  .page-subtitle { display: none; }

  .data-table {
    width: 100%;
    page-break-inside: avoid;
  }

  :deep(.el-table__header-wrapper) {
    display: table-row-group;
  }

  @page {
    size: landscape;
    margin: 1cm;
  }
}
</style>