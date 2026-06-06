<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1 class="page-title">数据看板</h1>
      <p class="page-subtitle">订单与 PI 合并数据汇总 — 确认数据无误后进入文档编辑</p>
    </div>

    <el-card class="dashboard-card">
      <template #header>
        <div class="card-header">
          <span>订单列表</span>
          <span class="card-hint">共 {{ total }} 条订单</span>
        </div>
      </template>

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
        :expand-row-keys="expandedRows"
        @expand-change="onExpandChange"
      >
        <el-table-column type="expand" width="50">
          <template #default="{ row }">
            <div class="product-expand">
              <div class="expand-header">
                <span class="expand-col">内部编码</span>
                <span class="expand-col">产品名称</span>
                <span class="expand-col">规格kg</span>
                <span class="expand-col">数量kg</span>
                <span class="expand-col">单价</span>
                <span class="expand-col">金额</span>
                <span class="expand-col">H.S.Code</span>
                <span class="expand-col">报关品名</span>
                <span class="expand-col">桶数</span>
                <span class="expand-col">托数</span>
                <span class="expand-col">毛重kg</span>
                <span class="expand-col">体积CBM</span>
                <span class="expand-col">20GP</span>
              </div>
              <div
                v-for="p in row.products"
                :key="p.id"
                class="expand-row"
              >
                <span class="expand-col mono">{{ p.internal_code }}</span>
                <span class="expand-col">{{ p.product_cn }}</span>
                <span class="expand-col">{{ p.spec_kg ?? '-' }}</span>
                <span class="expand-col">{{ p.quantity_kg ?? '-' }}</span>
                <span class="expand-col">{{ p.unit_price != null ? p.unit_price.toFixed(2) : '-' }}</span>
                <span class="expand-col">{{ p.total_amount != null ? p.total_amount.toFixed(2) : '-' }}</span>
                <span class="expand-col mono">{{ p.hs_code || '-' }}</span>
                <span class="expand-col">{{ p.customs_name || '-' }}</span>
                <span class="expand-col">{{ p.drum_count ?? '-' }}</span>
                <span class="expand-col">{{ p.pallet_count ?? '-' }}</span>
                <span class="expand-col">{{ p.gross_weight_kg != null ? p.gross_weight_kg.toFixed(1) : '-' }}</span>
                <span class="expand-col">{{ p.volume_cbm != null ? p.volume_cbm.toFixed(3) : '-' }}</span>
                <span class="expand-col">
                  <el-tag v-if="p.fits_20gp" :type="p.fits_20gp === '适合' ? 'success' : 'danger'" size="small">
                    {{ p.fits_20gp }}
                  </el-tag>
                  <span v-else>-</span>
                </span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="order_no" label="订单号" width="140" fixed />
        <el-table-column prop="customer_code" label="客户编码" width="120" />
        <el-table-column prop="salesperson" label="业务员" width="100" />
        <el-table-column prop="pi_no" label="PI号" width="120" />
        <el-table-column prop="product_count" label="产品数" width="80" align="center">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.product_count }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              type="danger"
              link
              size="small"
              icon="Delete"
              @click.stop="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 + 每页条数 -->
      <div class="pagination-wrapper no-print">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @current-change="loadData"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDashboardOrders, deleteDashboardOrder, type DashboardOrder } from '@/api/dashboard'

const searchText = ref('')
const orderList = ref<DashboardOrder[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const expandedRows = ref<number[]>([])

const loadData = async () => {
  loading.value = true
  try {
    const response = await getDashboardOrders({
      search: searchText.value || undefined,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    orderList.value = response.orders
    total.value = response.total
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  expandedRows.value = []
  loadData()
}

const handleSizeChange = () => {
  currentPage.value = 1
  expandedRows.value = []
  loadData()
}

const onExpandChange = (row: DashboardOrder, expanded: boolean[]) => {
  expandedRows.value = expanded.length
    ? [row.order_id]
    : []
}

const handleDelete = (row: DashboardOrder) => {
  ElMessageBox.confirm(
    `确定删除订单「${row.order_no}」及其所有产品吗？此操作不可撤销。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  ).then(async () => {
    try {
      await deleteDashboardOrder(row.order_id)
      ElMessage.success('删除成功')
      loadData()
    } catch {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const handleExportExcel = () => {
  const params: any = {}
  if (searchText.value) params.search = searchText.value
  window.location.href = `/api/v1/dashboard/export${searchText.value ? '?search=' + encodeURIComponent(searchText.value) : ''}`
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

.dashboard-card { border-radius: 12px; }
.card-header { font-weight: 600; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }
.card-hint { font-size: 12px; font-weight: 400; color: #909399; }

.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding: 12px 16px; background: #f5f7fa; border-radius: 8px; }
.toolbar-left { display: flex; gap: 12px; align-items: center; }
.toolbar-right { display: flex; gap: 8px; }
.search-input { width: 240px; }

.data-table { margin-bottom: 16px; }

/* 可展开产品区域 */
.product-expand {
  padding: 8px 0;
  background: #fafafa;
}
.expand-header {
  display: grid;
  grid-template-columns: 100px 1fr 70px 80px 70px 90px 80px 100px 60px 60px 80px 80px 70px;
  gap: 0;
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 600;
  color: #909399;
  border-bottom: 1px solid #eee;
  margin-bottom: 4px;
}
.expand-row {
  display: grid;
  grid-template-columns: 100px 1fr 70px 80px 70px 90px 80px 100px 60px 60px 80px 80px 70px;
  gap: 0;
  padding: 6px 12px;
  font-size: 12px;
  color: #606266;
  border-bottom: 1px solid #f0f0f0;
}
.expand-row:last-child { border-bottom: none; }
.expand-col { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.expand-col.mono { font-family: 'JetBrains Mono', monospace; font-size: 11px; }

.pagination-wrapper { display: flex; justify-content: flex-end; }

/* 打印样式 */
@media print {
  .toolbar, .no-print { display: none !important; }
  .page-header { margin-bottom: 12px; }
  .page-title { font-size: 20px; }
  .page-subtitle { display: none; }
  .data-table { width: 100%; page-break-inside: avoid; }
  :deep(.el-table__header-wrapper) { display: table-row-group; }
  @page { size: landscape; margin: 1cm; }
}
</style>