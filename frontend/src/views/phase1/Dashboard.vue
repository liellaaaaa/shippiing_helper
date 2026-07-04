<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1 class="page-title">台账列表</h1>
      <p class="page-subtitle">三源合并后的完整订单记录 — 选择一条记录进入文档编辑</p>
    </div>

    <el-card class="dashboard-card">
      <template #header>
        <div class="card-header">
          <span>订单台账</span>
          <span class="card-hint">共 {{ total }} 条记录</span>
        </div>
      </template>

      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchText"
            placeholder="搜索订单号 / 客户编码 / 业务员"
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
          <el-button type="primary" icon="Plus" @click="$router.push('/workflow')">
            新录入
          </el-button>
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
        :data="recordList"
        v-loading="loading"
        row-key="id"
        class="data-table"
        @row-click="handleRowClick"
      >
        <el-table-column prop="order_no" label="订单号/PI号" min-width="140" />
        <el-table-column prop="customer_code" label="客户编码" min-width="120" />
        <el-table-column prop="sales_person" label="业务员" min-width="100" />
        <el-table-column prop="consignee_name" label="收货人" min-width="140" show-overflow-tooltip />
        <el-table-column prop="destination" label="目的港" min-width="100" />
        <el-table-column prop="items.length" label="产品数" width="80" align="center">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.items?.length || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="录入时间" min-width="160">
          <template #default="{ row }">
            {{ row.created_at ? formatDate(row.created_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              icon="Document"
              @click.stop="handleEdit(row)"
            >
              进入文档编辑
            </el-button>
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

      <!-- 分页 -->
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

    <LedgerDetailDialog
      v-model="showDetailDialog"
      :record="selectedRecord"
      @edit="handleEdit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ordersApi, type LedgerRecord } from '@/api/orders'
import LedgerDetailDialog from './LedgerDetailDialog.vue'

const router = useRouter()

const searchText = ref('')
const recordList = ref<LedgerRecord[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showDetailDialog = ref(false)
const selectedRecord = ref<LedgerRecord | null>(null)

const loadData = async () => {
  loading.value = true
  try {
    const response = await ordersApi.listLedger({
      search: searchText.value || undefined,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    recordList.value = response.records
    total.value = response.total
  } catch (error) {
    ElMessage.error('加载台账失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadData()
}

const handleSizeChange = () => {
  currentPage.value = 1
  loadData()
}

const handleRowClick = (row: LedgerRecord) => {
  selectedRecord.value = row
  showDetailDialog.value = true
}

const handleEdit = (row: LedgerRecord) => {
  // 导航到 Phase2，传入台账记录ID
  // Phase2 需要改造为从台账ID读取数据
  router.push({ path: '/phase2', query: { ledgerId: String(row.id) } })
}

const handleDelete = (row: LedgerRecord) => {
  ElMessageBox.confirm(
    `确定删除台账记录「${row.order_no}」吗？此操作不可撤销。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  ).then(async () => {
    try {
      // TODO: 添加台账删除API
      ElMessage.info('删除功能待实现')
    } catch {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
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

const handleExportExcel = () => {
  ElMessage.info('导出功能待实现')
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
.search-input { width: 280px; }

.data-table { margin-bottom: 16px; width: 100%; }

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
