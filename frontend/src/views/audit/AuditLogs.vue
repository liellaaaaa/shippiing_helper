<template>
  <div class="audit-logs-page">
    <el-card>
      <template #header>
        <span>行为日志</span>
        <el-button type="primary" @click="handleExport">导出 Excel</el-button>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="用户名">
          <el-input v-model="filters.user_name" placeholder="用户名" clearable />
        </el-form-item>
        <el-form-item label="事件类型">
          <el-select v-model="filters.event_type" placeholder="全部" clearable>
            <el-option label="user_login" value="user_login" />
            <el-option label="enter_module" value="enter_module" />
            <el-option label="exit_module" value="exit_module" />
            <el-option label="save_to_database" value="save_to_database" />
            <el-option label="generate_document" value="generate_document" />
            <el-option label="system_health_check" value="system_health_check" />
          </el-select>
        </el-form-item>
        <el-form-item label="模块">
          <el-select v-model="filters.module" placeholder="全部" clearable>
            <el-option label="Phase1" value="phase1" />
            <el-option label="Phase2" value="phase2" />
            <el-option label="Phase3" value="phase3" />
            <el-option label="Dashboard" value="dashboard" />
            <el-option label="DataCenter" value="data-center" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadLogs">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="logs" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="event_type" label="事件类型" width="180" />
        <el-table-column prop="user_name" label="用户名" width="120" />
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="action_time" label="发生时间" width="180" />
        <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP" width="130" />
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadLogs"
        @size-change="loadLogs"
        style="margin-top: 16px"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { auditApi, type AuditLog } from '@/api/audit'
import { ElMessage } from 'element-plus'

const logs = ref<AuditLog[]>([])
const loading = ref(false)

const filters = reactive({
  user_name: '',
  event_type: '',
  module: '',
})

const pagination = reactive({
  page: 1,
  pageSize: 50,
  total: 0,
})

async function loadLogs() {
  loading.value = true
  try {
    const result = await auditApi.getLogs({
      user_name: filters.user_name || undefined,
      event_type: filters.event_type || undefined,
      module: filters.module || undefined,
      page: pagination.page,
      page_size: pagination.pageSize,
    })
    logs.value = result.logs
    pagination.total = result.total
  } catch {
    ElMessage.error('加载日志失败')
  } finally {
    loading.value = false
  }
}

function handleExport() {
  auditApi.exportExcel()
}

onMounted(loadLogs)
</script>

<style scoped>
.audit-logs-page {
  padding: 20px;
}
.filter-form {
  margin-bottom: 16px;
}
</style>
