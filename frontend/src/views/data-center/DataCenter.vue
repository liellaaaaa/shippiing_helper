<template>
  <div class="data-center-page">
    <div class="page-header">
      <h1 class="page-title">数据中心</h1>
      <p class="page-subtitle">references/ 文档管理中心</p>
    </div>

    <div class="dc-layout">
      <!-- 左侧目录树面板 -->
      <div class="dc-panel">
        <el-card class="dc-card">
          <template #header>
            <div class="card-header">
              <span>目录树</span>
              <span class="card-hint">{{ totalCount }} 个文件</span>
            </div>
          </template>

          <!-- 搜索 -->
          <div class="search-bar">
            <el-input
              v-model="searchQuery"
              placeholder="输入关键词搜索..."
              size="large"
              clearable
            >
             <template #append>
                <el-button>搜索</el-button>
              </template>
            </el-input>
          </div>

          <!-- 完整目录树 -->
          <div class="file-tree-wrapper">
            <el-tree
              :data="filteredTree"
              :props="{ children: 'children', label: 'label', isLeaf: 'isLeaf' }"
              node-key="key"
              default-expand-all
              @node-click="onTreeNodeClick"
              class="file-tree"
            >
              <template #default="{ node, data }">
                <span class="tree-node">
                  <span class="node-icon">{{ getFileIcon(data) }}</span>
                  <span class="node-label">{{ node.label }}</span>
                </span>
              </template>
            </el-tree>
          </div>
        </el-card>
      </div>

      <!-- 右侧预览面板 -->
      <div class="dc-preview-panel">
        <el-card class="dc-card" style="height: 100%;">
          <template #header>
            <div class="card-header">
              <span>文件预览</span>
              <span v-if="previewFilename" class="card-hint">{{ previewFilename }}</span>
            </div>
          </template>

          <!-- PDF 预览 -->
          <template v-if="selectedNode && selectedNode.file_type === 'pdf'">
            <iframe
              :src="`/api/v1/data-center/file?path=${encodeURIComponent(selectedNode.file_path || '')}&t=${Date.now()}`"
              class="pdf-iframe"
              frameborder="0"
            />
          </template>

          <!-- Word 文档提示下载 -->
          <template v-else-if="selectedNode && (selectedNode.file_type === 'doc' || selectedNode.file_type === 'docx')">
            <div class="preview-hint">
              <el-icon size="48"><document /></el-icon>
              <p>Word 文档仅支持下载后查看</p>
              <el-button type="primary" @click="downloadFile">下载文档</el-button>
            </div>
          </template>

          <!-- Excel 提示下载 -->
          <template v-else-if="selectedNode && (selectedNode.file_type === 'xls' || selectedNode.file_type === 'xlsx')">
            <div class="preview-hint">
              <el-icon size="48"><document /></el-icon>
              <p>Excel 文档仅支持下载后查看</p>
              <el-button type="primary" @click="downloadFile">下载文档</el-button>
            </div>
          </template>

          <!-- JSON 文件显示内容 -->
          <template v-else-if="selectedNode && selectedNode.file_type === 'json'">
            <div class="preview-hint">
              <el-icon size="48"><document /></el-icon>
              <p>JSON配置文件</p>
              <el-button type="primary" @click="downloadFile">下载文件</el-button>
            </div>
          </template>

          <!-- 空状态 -->
          <div v-else class="preview-empty">
            <el-icon size="48"><folder /></el-icon>
            <p>点击左侧文件预览</p>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Folder } from '@element-plus/icons-vue'
import { phase2Api } from '@/api/phase2'

// ── Tree ─────────────────────────────────────────────────
interface TreeNode {
  label: string
  key: string
  isLeaf: boolean
  file_type: string
  file_path?: string
  children?: TreeNode[]
}

const fullTree = ref<TreeNode[]>([])
const searchQuery = ref('')
const selectedNode = ref<TreeNode | null>(null)
const previewFilename = ref<string | null>(null)
const totalCount = ref(0)

async function loadTree() {
  try {
    const res = await phase2Api.getDataCenterTree()
    fullTree.value = res.data.tree as TreeNode[]
    totalCount.value = res.data.total
  } catch (e) {
    ElMessage.error('加载目录树失败')
  }
}

function getFileIcon(data: TreeNode): string {
  const icons: Record<string, string> = {
    folder: '📁',
    pdf: '📄',
    doc: '📝',
    docx: '📝',
    xls: '📊',
    xlsx: '📊',
    json: '⚙️',
    other: '📎',
  }
  return icons[data.file_type] || '📎'
}

function filterTree(nodes: TreeNode[], query: string): TreeNode[] {
  return nodes.filter(n => {
    if (n.isLeaf) return n.label.toLowerCase().includes(query)
    if (n.children) {
      const filtered = filterTree(n.children, query)
      return filtered.length > 0
    }
    return false
  })
}

const filteredTree = computed(() => {
  if (!searchQuery.value.trim()) return fullTree.value
  return filterTree(fullTree.value, searchQuery.value.toLowerCase())
})

function onTreeNodeClick(data: TreeNode) {
  if (!data.isLeaf) return
  selectedNode.value = data
  previewFilename.value = data.label
}

function downloadFile() {
  if (!selectedNode.value?.file_path) return
  const url = `/api/v1/data-center/file?path=${encodeURIComponent(selectedNode.value.file_path)}`
  const a = document.createElement('a')
  a.href = url
  a.download = selectedNode.value.label
  a.target = '_blank'
  a.click()
}

onMounted(() => {
  loadTree()
})
</script>

<style scoped>
/* ── Page shell ─────────────────────────────────────── */
.data-center-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}
.page-header { margin-bottom: 20px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: #909399; margin: 0; }

/* ── 主体两栏布局 ─────────────────────────────────── */
.dc-layout {
  display: grid;
  grid-template-columns: 480px 1fr;
  gap: 20px;
  align-items: start;
}
.dc-panel, .dc-preview-panel { display: flex; flex-direction: column; }

/* ── Card ────────────────────────────────────────────── */
.dc-card { border-radius: 12px; }
.card-header { font-weight: 600; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }
.card-hint { font-size: 12px; font-weight: 400; color: #909399; }

/* ── 搜索 ─────────────────────────────────────────── */
.search-bar { margin-bottom: 16px; }
.search-bar :deep(.el-input__wrapper) { border-radius: 6px; }

/* ── Tree ──────────────────────────────────────────── */
.file-tree-wrapper {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  overflow: hidden;
  max-height: 600px;
  overflow-y: auto;
}
.file-tree {
  background: transparent;
}
.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.node-icon { font-size: 14px; }
.node-label {
  font-family: 'JetBrains Mono', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── PDF 预览 ─────────────────────────────────────── */
.pdf-iframe { width: 100%; height: 640px; border: none; border-radius: 8px; }
.preview-empty, .preview-hint {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 80px 0; color: var(--el-text-color-placeholder); font-size: 14px;
}
.preview-hint p, .preview-empty p { margin: 0; }
</style>