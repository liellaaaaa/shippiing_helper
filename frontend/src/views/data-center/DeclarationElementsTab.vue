<template>
  <div class="declaration-elements-tab">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-select
          v-model="selectedHsCode"
          filterable
          remote
          :remote-method="searchHsCodes"
          :loading="searchLoading"
          placeholder="搜索或选择商品编码..."
          clearable
          style="width: 320px"
          @change="handleHsCodeChange"
          @clear="handleHsCodeClear"
        >
          <el-option
            v-for="item in hsCodeOptions"
            :key="item.hs_code"
            :label="`${item.hs_code} - ${item.website_name || ''}`"
            :value="item.hs_code"
          >
            <span>{{ item.hs_code }}</span>
            <span style="color: #8492a6; font-size: 12px; margin-left: 8px">
              {{ item.website_name }} ({{ item.product_count }}个产品)
            </span>
          </el-option>
        </el-select>
        <el-button type="primary" @click="openAddProduct" :disabled="!selectedHsCode">
          新增产品
        </el-button>
      </div>
      <div class="toolbar-right" v-if="currentDetail">
        <span class="hs-code-info">
          {{ currentDetail.hs_code }} - {{ currentDetail.website_name }}
        </span>
      </div>
    </div>

    <!-- 内容区域 -->
    <div v-if="selectedHsCode && currentDetail" class="content-area">
      <!-- 产品表格 -->
      <el-table
        :data="currentDetail.products"
        v-loading="loading"
        border
        stripe
        style="width: 100%"
        max-height="calc(100vh - 320px)"
      >
        <!-- 固定列：商品名称 -->
        <el-table-column prop="product_name" label="商品名称" width="180" fixed="left">
          <template #default="{ row }">
            <div class="cell-editable" @click="openEditProduct(row)">
              {{ row.product_name }}
            </div>
          </template>
        </el-table-column>

        <!-- 动态列：根据字段定义渲染 -->
        <el-table-column
          v-for="field in currentDetail.fields"
          :key="field.field_name"
          :label="field.field_name"
          :min-width="getColumnWidth(field.field_name)"
        >
          <template #default="{ row }">
            <div
              class="cell-editable"
              :class="{ 'cell-empty': !row.values[field.field_name] }"
              @click="startEdit(row.id, field.field_name, row.values[field.field_name] || '')"
            >
              <template v-if="editingCell?.productId === row.id && editingCell?.fieldName === field.field_name">
                <el-input
                  v-model="editingCell.value"
                  size="small"
                  :autosize="{ minRows: 1, maxRows: 4 }"
                  type="textarea"
                  @blur="finishEdit"
                  @keyup.enter="finishEdit"
                  ref="editInput"
                />
              </template>
              <template v-else>
                {{ row.values[field.field_name] || '-' }}
              </template>
            </div>
          </template>
        </el-table-column>

        <!-- 操作列 -->
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-popconfirm
              title="确认删除此产品？"
              @confirm="handleDeleteProduct(row.id)"
            >
              <template #reference>
                <el-button type="danger" link size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <el-empty description="请选择商品编码查看申报要素" />
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
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { declarationLedgerApi, type HsCodeListItem, type HsCodeDetail, type DeclarationProduct } from '@/api/declaration-ledger'
import ProductEditDialog from './ProductEditDialog.vue'

const hsCodeOptions = ref<HsCodeListItem[]>([])
const selectedHsCode = ref<string>('')
const currentDetail = ref<HsCodeDetail | null>(null)
const loading = ref(false)
const searchLoading = ref(false)

// 编辑单元格状态
const editingCell = ref<{
  productId: number
  fieldName: string
  value: string
} | null>(null)

// 产品弹窗状态
const productDialogVisible = ref(false)
const editingProduct = ref<DeclarationProduct | null>(null)

// 搜索 HS Code
async function searchHsCodes(query: string) {
  if (!query) {
    hsCodeOptions.value = []
    return
  }
  searchLoading.value = true
  try {
    const res = await declarationLedgerApi.listHsCodes(query)
    hsCodeOptions.value = res.data
  } catch {
    ElMessage.error('搜索失败')
  } finally {
    searchLoading.value = false
  }
}

// HS Code 变化
async function handleHsCodeChange(hsCode: string) {
  if (!hsCode) {
    currentDetail.value = null
    return
  }
  await loadHsCodeDetail(hsCode)
}

// 清除选择
function handleHsCodeClear() {
  selectedHsCode.value = ''
  currentDetail.value = null
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

// 开始编辑单元格
function startEdit(productId: number, fieldName: string, value: string) {
  editingCell.value = { productId, fieldName, value }
  nextTick(() => {
    const input = document.querySelector('.cell-editable .el-textarea__inner') as HTMLTextAreaElement
    if (input) {
      input.focus()
    }
  })
}

// 完成编辑
async function finishEdit() {
  if (!editingCell.value) return

  const { productId, fieldName, value } = editingCell.value
  editingCell.value = null

  try {
    await declarationLedgerApi.updateValues(productId, {
      values: { [fieldName]: value }
    })
    // 更新本地数据
    if (currentDetail.value) {
      const product = currentDetail.value.products.find(p => p.id === productId)
      if (product) {
        product.values[fieldName] = value
      }
    }
    ElMessage.success('保存成功')
  } catch {
    ElMessage.error('保存失败')
  }
}

// 获取列宽
function getColumnWidth(fieldName: string): number {
  const length = fieldName.length
  if (length <= 4) return 120
  if (length <= 6) return 150
  if (length <= 10) return 180
  return 200
}

// 打开新增产品弹窗
function openAddProduct() {
  editingProduct.value = null
  productDialogVisible.value = true
}

// 打开编辑产品弹窗
function openEditProduct(product: DeclarationProduct) {
  editingProduct.value = { ...product }
  productDialogVisible.value = true
}

// 删除产品
async function handleDeleteProduct(productId: number) {
  try {
    await declarationLedgerApi.deleteProduct(productId)
    ElMessage.success('删除成功')
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

// 初始化加载 HS Code 列表
onMounted(async () => {
  try {
    const res = await declarationLedgerApi.listHsCodes()
    hsCodeOptions.value = res.data
  } catch {
    ElMessage.error('加载 HS Code 列表失败')
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

.cell-editable {
  cursor: pointer;
  padding: 4px 8px;
  min-height: 32px;
  display: flex;
  align-items: center;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.cell-editable:hover {
  background-color: var(--el-fill-color-light);
}

.cell-empty {
  color: var(--el-text-color-placeholder);
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
}
</style>
