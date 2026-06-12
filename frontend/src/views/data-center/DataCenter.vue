<template>
  <div class="data-center-page">
    <div class="page-header">
      <h1 class="page-title">数据中心</h1>
      <p class="page-subtitle">查询 MSDS 参考文件 · 运输鉴定报告</p>
    </div>

    <div class="toolbar-tabs">
      <el-radio-group v-model="activeTab">
        <el-radio-button value="msds">MSDS查询</el-radio-button>
        <el-radio-button value="transport">运输鉴定报告</el-radio-button>
      </el-radio-group>
    </div>

    <div class="dc-layout">
      <!-- 左侧搜索面板 -->
      <div class="dc-panel">
        <el-card class="dc-card">
          <template #header>
            <div class="card-header">
              <span>{{ activeTab === 'msds' ? 'MSDS 参考文件' : '运输鉴定报告' }}</span>
              <span class="card-hint">{{ activeTab === 'msds' ? '搜索并预览参考文件' : '搜索 PDF 文件' }}</span>
            </div>
          </template>

          <!-- MSDS 搜索 -->
          <div v-if="activeTab === 'msds'" class="search-bar">
            <el-input
              v-model="msdsQuery"
              placeholder="输入关键词搜索 MSDS，如 柔软、皂洗、固色"
              size="large"
              clearable
              @keyup.enter="searchMsds"
            >
              <template #append>
                <el-button @click="searchMsds">搜索</el-button>
              </template>
            </el-input>
          </div>

          <!-- 运输鉴定搜索 -->
          <div v-else class="search-bar">
            <el-input
              v-model="trQuery"
              placeholder="输入关键词搜索运输鉴定报告，如 除油、匀染"
              size="large"
              clearable
              @keyup.enter="searchTransport"
            >
              <template #append>
                <el-button @click="searchTransport">搜索</el-button>
              </template>
            </el-input>
          </div>

          <!-- File Tree -->
          <div class="file-tree-wrapper">
            <el-tree
              v-if="activeTab === 'msds'"
              :data="filteredMsdsTree"
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
            <el-tree
              v-else
              :data="filteredTransportTree"
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

          <!-- MSDS 选中摘要 -->
          <div v-if="activeTab === 'msds' && msdsSelectedId && msdsSummary.product_name_cn" class="summary-section">
            <el-divider content-position="left">文件摘要</el-divider>
            <div class="summary-grid">
              <div class="summary-row"><span class="summary-label">产品名称</span><span class="summary-value">{{ msdsSummary.product_name_cn }}</span></div>
              <div class="summary-row"><span class="summary-label">物理形态</span><span class="summary-value">{{ msdsSummary.physical_form || '—' }}</span></div>
              <div class="summary-row"><span class="summary-label">离子类型</span><span class="summary-value">{{ msdsSummary.ion_type || '—' }}</span></div>
              <div class="summary-row"><span class="summary-label">pH值</span><span class="summary-value">{{ msdsSummary.ph || '—' }}</span></div>
            </div>
            <div class="action-row">
              <el-button size="small" @click="downloadMsds">下载文件</el-button>
              <el-button type="primary" size="small" @click="msdsUploadDialogVisible = true">修正上传</el-button>
            </div>
          </div>

          <!-- 运输鉴定选中摘要 -->
          <div v-if="activeTab === 'transport' && trSelectedFilename && trFields.report_no" class="summary-section">
            <el-divider content-position="left">文件摘要</el-divider>
            <div class="summary-grid">
              <div class="summary-row"><span class="summary-label">报告编号</span><span class="summary-value">{{ trFields.report_no }}</span></div>
              <div class="summary-row"><span class="summary-label">样品描述</span><span class="summary-value">{{ trFields.sample_description || '—' }}</span></div>
            </div>
            <div class="action-row">
              <el-button type="primary" size="small" @click="downloadTransport">下载PDF</el-button>
            </div>
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

          <!-- MSDS PDF 预览 -->
          <template v-if="activeTab === 'msds' && msdsSelectedId && msdsSummary.file_format === 'pdf'">
            <iframe
              :src="`/api/v1/data-center/files/${msdsSelectedId}?t=${Date.now()}`"
              class="pdf-iframe"
              frameborder="0"
            />
          </template>
          <template v-else-if="activeTab === 'msds' && msdsSelectedId && msdsSummary.file_format === 'doc'">
            <div class="preview-hint">
              <el-icon size="48"><document /></el-icon>
              <p>Word 文档仅支持下载后查看</p>
              <el-button type="primary" @click="downloadMsds">下载 DOC</el-button>
            </div>
          </template>

          <!-- 运输鉴定 PDF 预览 -->
          <template v-if="activeTab === 'transport' && trSelectedFilename">
            <iframe
              :src="`/api/v1/transport-reports/files/${encodeURIComponent(trSelectedFilename)}?t=${Date.now()}`"
              class="pdf-iframe"
              frameborder="0"
            />
          </template>

          <!-- 空状态 -->
          <div v-if="!previewFilename" class="preview-empty">
            <el-icon size="48"><folder /></el-icon>
            <p>点击左侧搜索结果预览文件</p>
          </div>
        </el-card>
      </div>
    </div>

    <!-- MSDS 修正上传弹窗 -->
    <el-dialog v-model="msdsUploadDialogVisible" title="修正上传 MSDS" width="440px">
      <div class="upload-dialog-body">
        <p class="upload-hint">上传修正后的 MSDS 文件（系统将保留原文件，以时间戳命名新版本）：</p>
        <input ref="msdsUploadInput" type="file" accept=".pdf,.doc,.docx" style="display:none" @change="onMsdsUploadFileSelected" />
        <div class="upload-zone" @click="(msdsUploadInput as any)?.click()">
          <el-icon size="32"><upload-filled /></el-icon>
          <p class="upload-text">点击选择文件</p>
          <p class="upload-hint-sub">PDF / DOC / DOCX</p>
        </div>
        <div v-if="msdsUploadFileName" class="upload-file-name">
          <el-icon><check /></el-icon> 已选择：{{ msdsUploadFileName }}
        </div>
      </div>
      <template #footer>
        <el-button @click="msdsUploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="msdsUploading" :disabled="!msdsUploadFileName" @click="confirmMsdsUpload">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Folder, UploadFilled, Check } from '@element-plus/icons-vue'
import { phase2Api } from '@/api/phase2'

const activeTab = ref<'msds' | 'transport'>('msds')

// ── Tree ─────────────────────────────────────────────────
interface TreeNode {
  label: string
  key: string
  isLeaf: boolean
  file_type: string
  file_path?: string
  children?: TreeNode[]
}

const msdsTree = ref<TreeNode[]>([])
const transportTree = ref<TreeNode[]>([])

async function loadTree() {
  try {
    const res = await phase2Api.getDataCenterTree()
    const tree = res.data.tree as TreeNode[]
    const msdsNode = tree.find(n => n.label === 'MSDS')
    const transportNode = tree.find(n => n.label === '海运鉴定报告')
    msdsTree.value = msdsNode?.children || []
    transportTree.value = transportNode?.children || []
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

function onFileClick(data: TreeNode) {
  if (!data.isLeaf) return
  selectedFile.value = data
  previewFilename.value = data.label
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

const filteredMsdsTree = computed(() => {
  if (!msdsQuery.value.trim()) return msdsTree.value
  const query = msdsQuery.value.toLowerCase()
  return filterTree(msdsTree.value, query)
})

const filteredTransportTree = computed(() => {
  if (!trQuery.value.trim()) return transportTree.value
  const query = trQuery.value.toLowerCase()
  return filterTree(transportTree.value, query)
})

onMounted(() => {
  loadTree()
})

watch(activeTab, loadTree)

// ── MSDS ───────────────────────────────────────────────
interface MsdsResult {
  id: number
  filename: string
  product_name_cn: string
  physical_form: string
  ion_type: string
  ph: string
  file_format: string
  match_type: string
  file_path: string
}

const msdsQuery = ref('')
const msdsSelectedId = ref<number | null>(null)
const msdsSummary = ref<Partial<MsdsResult>>({})
const msdsUploadDialogVisible = ref(false)
const msdsUploadInput = ref<HTMLInputElement>()
const msdsUploadFileName = ref('')
const msdsUploading = ref(false)
const msdsFileToUpload = ref<File | null>(null)

const previewFilename = computed(() => {
  if (activeTab.value === 'msds') return msdsSummary.value.filename || null
  return trSelectedFilename.value || null
})

function searchMsds() {
  // Filtering is handled by computed property filteredMsdsTree
}

function selectMsds(r: MsdsResult) {
  msdsSelectedId.value = r.id
  msdsSummary.value = r
}

function onTreeNodeClick(data: TreeNode) {
  if (!data.isLeaf) return
  selectedFile.value = data
  if (activeTab.value === 'msds') {
    msdsSelectedId.value = parseInt(data.key)
    msdsSummary.value = { ...msdsSummary.value, filename: data.label, file_format: data.file_type }
  } else {
    trSelectedFilename.value = data.label
    trFields.value = { report_no: data.label, sample_description: '' }
  }
  previewFilename.value = data.label
}

function downloadMsds() {
  if (!msdsSelectedId.value) return
  const url = phase2Api.getDataCenterFileUrl(msdsSelectedId.value)
  const a = document.createElement('a')
  a.href = url
  a.download = msdsSummary.value.filename || 'msds'
  a.target = '_blank'
  a.click()
}

function onMsdsUploadFileSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  msdsFileToUpload.value = file
  msdsUploadFileName.value = file.name
}

async function confirmMsdsUpload() {
  if (!msdsFileToUpload.value || !msdsSelectedId.value) return
  msdsUploading.value = true
  try {
    await phase2Api.uploadCorrectedMsds(msdsSelectedId.value, msdsFileToUpload.value)
    ElMessage.success('上传成功')
    msdsUploadDialogVisible.value = false
    msdsFileToUpload.value = null
    msdsUploadFileName.value = ''
  } catch { ElMessage.error('上传失败') }
  finally { msdsUploading.value = false }
}

// ── 运输鉴定报告 ───────────────────────────────────────
interface TransportResult {
  id: number
  filename: string
  report_no: string
  sample_description: string
  match_type: string
}

const trQuery = ref('')
const trSelectedFilename = ref<string | null>(null)
const trFields = ref({ report_no: '', sample_description: '' })

function searchTransport() {
  // Filtering is handled by computed property filteredTransportTree
}

function selectTransport(r: TransportResult) {
  trSelectedFilename.value = r.filename
  trFields.value = { report_no: r.report_no, sample_description: r.sample_description }
}

function downloadTransport() {
  if (!trSelectedFilename.value) return
  const url = phase2Api.getTransportReportFileUrl(trSelectedFilename.value)
  const a = document.createElement('a')
  a.href = url
  a.download = trSelectedFilename.value
  a.target = '_blank'
  a.click()
}
</script>

<style scoped>
/* ── Page shell（参考 Phase1Workflow）────────────── */
.data-center-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}
.page-header { margin-bottom: 20px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: #909399; margin: 0; }

/* ── Tab 切换 ───────────────────────────────── */
.toolbar-tabs { margin-bottom: 20px; }

/* ── 主体两栏布局 ─────────────────────────────── */
.dc-layout {
  display: grid;
  grid-template-columns: 480px 1fr;
  gap: 20px;
  align-items: start;
}
.dc-panel, .dc-preview-panel { display: flex; flex-direction: column; }

/* ── Card ─────────────────────────────────── */
.dc-card { border-radius: 12px; }
.card-header { font-weight: 600; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }
.card-hint { font-size: 12px; font-weight: 400; color: #909399; }

/* ── 搜索 ───────────────────────────────── */
.search-bar { margin-bottom: 16px; }
.search-bar :deep(.el-input__wrapper) { border-radius: 6px; }

/* ── 结果列表 ─────────────────────────────── */
.results-list {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  overflow: hidden;
  max-height: 280px;
  overflow-y: auto;
}
.result-item {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-light);
  transition: background 0.15s;
}
.result-item:last-child { border-bottom: none; }
.result-item:hover { background: var(--el-fill-color-light); }
.result-item--selected { background: var(--el-color-primary-light-9); }
.result-main { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.result-filename { flex: 1; font-size: 12px; font-family: 'JetBrains Mono', monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.result-product { font-size: 11px; color: var(--el-text-color-secondary); }

.empty-hint { display: flex; align-items: center; gap: 6px; justify-content: center; padding: 24px; color: var(--el-text-color-placeholder); font-size: 13px; }

/* ── Tree ─────────────────────────────────── */
.file-tree-wrapper {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  overflow: hidden;
  max-height: 400px;
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

/* ── 摘要 ───────────────────────────────── */
.summary-section { margin-top: 16px; }
.summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.summary-row { display: flex; gap: 8px; font-size: 13px; }
.summary-label { color: var(--el-text-color-secondary); flex-shrink: 0; min-width: 60px; }
.summary-value { color: var(--el-text-color-primary); font-family: 'JetBrains Mono', monospace; }

.action-row { display: flex; gap: 8px; margin-top: 12px; }

/* ── PDF 预览 ─────────────────────────────── */
.pdf-iframe { width: 100%; height: 640px; border: none; border-radius: 8px; }
.preview-empty, .preview-hint {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 80px 0; color: var(--el-text-color-placeholder); font-size: 14px;
}
.preview-hint p, .preview-empty p { margin: 0; }

/* ── 上传弹窗 ─────────────────────────────── */
.upload-dialog-body { padding: 8px 0; }
.upload-hint { font-size: 13px; color: var(--el-text-color-secondary); margin-bottom: 16px; }
.upload-zone {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; padding: 32px 0;
  border: 1.5px dashed var(--el-border-color);
  border-radius: 8px; cursor: pointer; transition: border-color 0.2s, color 0.2s;
  color: var(--el-text-color-secondary);
}
.upload-zone:hover { border-color: var(--el-color-primary); color: var(--el-color-primary); }
.upload-text { margin: 0; font-size: 14px; }
.upload-hint-sub { margin: 0; font-size: 12px; color: var(--el-text-color-placeholder); }
.upload-file-name { margin-top: 10px; font-size: 12px; color: var(--el-color-success); display: flex; align-items: center; gap: 4px; }
</style>
