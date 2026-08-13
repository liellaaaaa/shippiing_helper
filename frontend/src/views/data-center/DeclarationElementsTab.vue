<template>
  <div class="declaration-elements-tab">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="selectedHsCode"
          filterable
          placeholder="选择商品编码..."
          style="width: 340px"
          @change="handleHsCodeChange"
          @visible-change="handleDropdownVisible"
        >
          <el-option
            v-for="item in hsCodeOptions"
            :key="item.hs_code"
            :label="`${item.hs_code} - ${item.website_name || ''}（${item.product_count}个产品）`"
            :value="item.hs_code"
          />
        </el-select>
        <el-button type="primary" @click="openAddProduct">新增产品</el-button>
      </div>
      <div class="toolbar-right" v-if="currentDetail">
        <span class="hs-code-info">
          {{ currentDetail.hs_code }} - {{ currentDetail.website_name }}（{{ currentDetail.products.length }} 个产品）
        </span>
      </div>
    </div>

    <!-- 内容区域 -->
    <div v-if="currentDetail" class="content-area">
      <el-table
        :data="currentDetail.products"
        v-loading="loading"
        border
        stripe
        highlight-current-row
        style="width: 100%"
        max-height="calc(100vh - 360px)"
        @current-change="onRowClick"
      >
        <!-- 商品名称 -->
        <el-table-column prop="product_name" label="商品名称" min-width="160" show-overflow-tooltip />

        <!-- 动态列：根据字段定义渲染（列宽按内容自适应） -->
        <el-table-column
          v-for="field in currentDetail.fields"
          :key="field.field_name"
          :label="field.field_name"
          min-width="130"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span :class="{ 'cell-empty': !row.values[field.field_name] }">
              {{ row.values[field.field_name] || '-' }}
            </span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 选中行操作按钮（仿 MSDS 台账：选中后操作，弹窗编辑） -->
      <div v-if="selectedRow" class="detail-actions">
        <el-button size="small" @click="openEditProduct">编辑</el-button>
        <el-popconfirm title="确认删除此产品？" @confirm="handleDeleteProduct">
          <template #reference>
            <el-button size="small" type="danger">删除</el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <el-empty description="暂无申报要素数据" />
    </div>

    <!-- 新增/编辑产品弹窗 -->
    <ProductEditDialog
      v-model="productDialogVisible"
      :hs-code="selectedHsCode"
      :product="editingProduct"
      :fields="currentDetail?.fields || []"
      @saved="handleProductSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { declarationLedgerApi, type HsCodeListItem, type HsCodeDetail, type DeclarationProduct } from '@/api/declaration-ledger'
import ProductEditDialog from './ProductEditDialog.vue'

const hsCodeOptions = ref<HsCodeListItem[]>([])
const allHsCodeOptions = ref<HsCodeListItem[]>([])  // 缓存所有选项
const selectedHsCode = ref('')
const currentDetail = ref<HsCodeDetail | null>(null)
const loading = ref(false)
const selectedRow = ref<DeclarationProduct | null>(null)

// 产品弹窗状态
const productDialogVisible = ref(false)
const editingProduct = ref<DeclarationProduct | null>(null)

// 下拉框显示时，如果有缓存就用缓存，否则重新加载
async function handleDropdownVisible(visible: boolean) {
  if (visible && allHsCodeOptions.value.length === 0) {
    await loadAllHsCodes()
  }
  hsCodeOptions.value = allHsCodeOptions.value
}

// 加载所有 HS Code
async function loadAllHsCodes() {
  try {
    const res = await declarationLedgerApi.listHsCodes()
    allHsCodeOptions.value = res.data
    hsCodeOptions.value = res.data
  } catch {
    ElMessage.error('加载 HS Code 列表失败')
  }
}

// 切换 HS Code
async function handleHsCodeChange(hsCode: string) {
  if (!hsCode) return
  selectedRow.value = null
  await loadHsCodeDetail(hsCode)
}

// 加载 HS Code 详情
async function loadHsCodeDetail(hsCode: string) {
  loading.value = true
  try {
    const res = await declarationLedgerApi.getHsCodeDetail(hsCode)
    currentDetail.value = res.data
  } catch {
    ElMessage.error('加载数据失败')
    currentDetail.value = null
  } finally {
    loading.value = false
  }
}

// 行选中
function onRowClick(row: DeclarationProduct | null) {
  selectedRow.value = row
}

// 打开新增产品弹窗
function openAddProduct() {
  editingProduct.value = null
  productDialogVisible.value = true
}

// 打开编辑产品弹窗
function openEditProduct() {
  if (!selectedRow.value) return
  editingProduct.value = { ...selectedRow.value }
  productDialogVisible.value = true
}

// 删除产品
async function handleDeleteProduct() {
  if (!selectedRow.value) return
  try {
    await declarationLedgerApi.deleteProduct(selectedRow.value.id)
    ElMessage.success('删除成功')
    selectedRow.value = null
    if (selectedHsCode.value) {
      await loadHsCodeDetail(selectedHsCode.value)
    }
  } catch {
    ElMessage.error('删除失败')
  }
}

// 产品保存成功
async function handleProductSaved() {
  if (selectedHsCode.value) {
    await loadHsCodeDetail(selectedHsCode.value)
  }
}

// 初始化：加载 HS Code 列表并默认选中第一个，打开页面直接展示数据
onMounted(async () => {
  await loadAllHsCodes()
  if (allHsCodeOptions.value.length > 0) {
    selectedHsCode.value = allHsCodeOptions.value[0].hs_code
    await loadHsCodeDetail(selectedHsCode.value)
  }
})
</script>

<style scoped>
.declaration-elements-tab {
  padding: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.toolbar-right {
  display: flex;
  align-items: center;
}

.hs-code-info {
  font-size: 14px;
  color: var(--el-text-color-regular);
  font-weight: 500;
}

.content-area {
  background: var(--el-bg-color);
  border-radius: 4px;
}

.cell-empty {
  color: var(--el-text-color-placeholder);
}

.detail-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  align-items: center;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
}
</style>
