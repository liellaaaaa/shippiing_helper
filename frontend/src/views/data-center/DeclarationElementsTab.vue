<template>
  <div class="declaration-elements-tab">
    <!-- 搜索栏 -->
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索商品编码或申报名称..."
        clearable
        style="width: 320px"
        @keyup.enter="loadData(1)"
        @clear="loadData(1)"
      >
        <template #append>
          <el-button @click="loadData(1)">搜索</el-button>
        </template>
      </el-input>
      <el-button type="primary" @click="openAdd">新增</el-button>
    </div>

    <!-- 表格 -->
    <el-table
      :data="items"
      v-loading="loading"
      border
      stripe
      style="width: 100%"
      max-height="calc(100vh - 280px)"
    >
      <el-table-column prop="hs_code" label="商品编码" width="150" />
      <el-table-column prop="declaration_name" label="申报名称" width="200" />
      <el-table-column prop="elements_text" label="申报要素" min-width="300">
        <template #default="{ row }">
          <span class="elements-text">{{ row.elements_text }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm
            title="确认删除此条记录？"
            @confirm="handleDelete(row.id)"
          >
            <template #reference>
              <el-button type="danger" link size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination" v-if="total > 0">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </div>

    <!-- 编辑弹窗 -->
    <ElementEditDialog
      v-model="dialogVisible"
      :element="editingElement"
      @saved="loadData(page)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { declarationElementsApi, type DeclarationElement } from '@/api/declaration-elements'
import ElementEditDialog from './ElementEditDialog.vue'

const items = ref<DeclarationElement[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 50
const keyword = ref('')
const loading = ref(false)

const dialogVisible = ref(false)
const editingElement = ref<DeclarationElement | null>(null)

async function loadData(p?: number) {
  if (p) page.value = p
  loading.value = true
  try {
    const res = await declarationElementsApi.list({
      keyword: keyword.value || undefined,
      page: page.value,
      size: pageSize,
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  editingElement.value = null
  dialogVisible.value = true
}

function openEdit(row: DeclarationElement) {
  editingElement.value = { ...row }
  dialogVisible.value = true
}

async function handleDelete(id: number) {
  try {
    await declarationElementsApi.delete(id)
    ElMessage.success('已删除')
    loadData(page.value)
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(() => loadData(1))
</script>

<style scoped>
.declaration-elements-tab {
  padding: 0;
}
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
.elements-text {
  font-size: 13px;
  color: var(--el-text-color-regular);
  word-break: break-all;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
