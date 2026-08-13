<template>
  <div class="dashboard-page">
    <el-tabs v-model="activeTab" class="dashboard-tabs">
      <!-- 第一个 tab：订单台账 -->
      <el-tab-pane label="订单台账" name="orders">
        <el-card class="dashboard-card">
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
              <span class="record-count">共 {{ total }} 条记录</span>
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
                <el-tag type="info" size="small">{{ visibleItemCount(row.items) }}</el-tag>
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
      </el-tab-pane>

      <!-- 第二个 tab：申报要素台账 -->
      <el-tab-pane label="申报要素" name="declaration">
        <el-card class="dashboard-card">
          <DeclarationElementsTab />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <LedgerDetailDialog
      v-model="showDetailDialog"
      :record="selectedRecord"
      @edit="handleEdit"
      @saved="handleSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ordersApi, type LedgerRecord } from '@/api/orders'
import LedgerDetailDialog from './LedgerDetailDialog.vue'
import DeclarationElementsTab from '@/views/data-center/DeclarationElementsTab.vue'

const router = useRouter()

const activeTab = ref('orders')
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

const handleSaved = async () => {
  await loadData()
  if (selectedRecord.value) {
    const updated = recordList.value.find(r => r.order_no === selectedRecord.value!.order_no)
    if (updated) selectedRecord.value = updated
  }
}

const handleEdit = (row: LedgerRecord) => {
  router.push({ path: '/phase2', query: { ledgerId: String(row.id) } })
}

const handleDelete = (row: LedgerRecord) => {
  ElMessageBox.confirm(
    `确定删除台账记录「${row.order_no}」吗？此操作不可撤销。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  ).then(async () => {
    try {
      await ordersApi.deleteLedger(row.order_no)
      ElMessage.success(`已删除台账记录「${row.order_no}」`)
      loadData()
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

function visibleItemCount(items: any[] | undefined): number {
  if (!items) return 0
  return items.filter((it: any) => !(it.group_id != null && !it.is_group_header)).length
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

.dashboard-tabs { margin-bottom: 16px; }

.dashboard-card { border-radius: 12px; }

.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding: 12px 16px; background: #f5f7fa; border-radius: 8px; }
.toolbar-left { display: flex; gap: 12px; align-items: center; }
.toolbar-right { display: flex; gap: 8px; }
.search-input { width: 280px; }
.record-count { font-size: 13px; color: #909399; }

.data-table { margin-bottom: 16px; width: 100%; }

.pagination-wrapper { display: flex; justify-content: flex-end; }

@media print {
  .toolbar, .no-print { display: none !important; }
  .data-table { width: 100%; page-break-inside: avoid; }
  :deep(.el-table__header-wrapper) { display: table-row-group; }
  @page { size: landscape; margin: 1cm; }
}
</style>
