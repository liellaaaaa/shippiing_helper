<template>
  <div class="data-center-panel">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <input
        v-model="query"
        class="search-input"
        placeholder="输入关键词搜索MSDS，如 FIXING"
        @keyup.enter="search"
      />
      <button class="search-btn" @click="search" :disabled="loading">
        <span v-if="!loading">搜索</span>
        <span v-else>搜索中...</span>
      </button>
    </div>

    <!-- 结果列表 -->
    <div v-if="results.length" class="results-list">
      <div
        v-for="r in results"
        :key="r.id"
        class="result-item"
        :class="{ 'result-item--selected': selectedId === r.id }"
        @click="selectResult(r)"
      >
        <div class="result-main">
          <span class="result-filename">{{ r.filename }}</span>
          <span class="result-badge" :class="r.file_format">{{ r.file_format.toUpperCase() }}</span>
        </div>
        <div v-if="r.product_name_cn" class="result-product">{{ r.product_name_cn }}</div>
      </div>
    </div>

    <div v-else-if="searched && !loading" class="empty-state">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".3">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <span>无匹配结果</span>
    </div>

    <div v-else-if="!searched" class="empty-state">
      <span>输入关键词搜索MSDS参考文件</span>
    </div>

    <!-- 选中后的详情区：只在左侧显示摘要，右侧预览通过 emit 在 Phase2Workflow 中展示 -->
    <div v-if="selectedId && summary.product_name_cn" class="detail-panel">
      <!-- 左侧摘要 -->
      <div class="detail-left">
        <div class="field-row">
          <div class="field-label">产品名称</div>
          <div class="field-body field-body--readonly">{{ summary.product_name_cn || '—' }}</div>
        </div>
        <div class="field-row">
          <div class="field-label">物理形态</div>
          <div class="field-body field-body--readonly">{{ summary.physical_form || '—' }}</div>
        </div>
        <div class="field-row">
          <div class="field-label">离子类型</div>
          <div class="field-body field-body--readonly">{{ summary.ion_type || '—' }}</div>
        </div>
        <div class="field-row">
          <div class="field-label">pH值</div>
          <div class="field-body field-body--readonly">{{ summary.ph || '—' }}</div>
        </div>
        <div class="field-row">
          <div class="field-label">文件格式</div>
          <div class="field-body field-body--readonly">{{ summary.file_format?.toUpperCase() || '—' }}</div>
        </div>
        <div class="action-row">
          <button class="action-btn" @click="downloadFile">下载</button>
          <button class="action-btn action-btn--primary" @click="showUploadDialog = true">修正上传</button>
        </div>
      </div>
    </div>

    <!-- 修正上传弹窗 -->
    <el-dialog v-model="showUploadDialog" title="修正上传MSDS" width="420px">
      <div class="upload-dialog-body">
        <p class="upload-hint">上传修正后的 MSDS 文件（系统将保留原文件，以时间戳命名新版本）：</p>
        <input ref="uploadInput" type="file" accept=".pdf,.doc,.docx" style="display:none" @change="onUploadFileSelected" />
        <div class="upload-zone" @click="uploadInput?.click()">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".5">
            <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/>
            <path d="M20.39 18.39A5 5 0 0 1 18 18h-1.61a2 2 0 0 1-2-2V9l-3-3H9a2 2 0 0 1-2-2v-.61A5 5 0 0 1 9 4.61L7.1 7.58a2 2 0 0 1-2.83 0L2.41 9.41A2 2 0 0 1 4.24 11.66l4.24 4.24a2 2 0 0 1 0 2.83L7.17 17.59a2 2 0 1 1 2.83 0l4.24-4.24"/>
          </svg>
          <span>点击选择文件</span>
          <em>PDF / DOC / DOCX</em>
        </div>
        <div v-if="uploadFileName" class="upload-file-name">
          已选择：{{ uploadFileName }}
        </div>
      </div>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!uploadFileName" @click="confirmUpload">
          上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { phase2Api } from '@/api/phase2'

const emit = defineEmits<{
  (e: 'open-data-center-preview', file: { id: number; filename: string; file_format: string }): void
}>()

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

const query = ref('')
const loading = ref(false)
const searched = ref(false)
const results = ref<MsdsResult[]>([])
const selectedId = ref<number | null>(null)
const summary = ref<Partial<MsdsResult>>({})
const showUploadDialog = ref(false)
const uploadInput = ref<HTMLInputElement>()
const uploadFileName = ref('')
const uploading = ref(false)
const fileToUpload = ref<File | null>(null)


async function search() {
  if (!query.value.trim()) return
  loading.value = true
  searched.value = true
  try {
    const res = await phase2Api.searchDataCenter(query.value)
    results.value = res.data.items || []
  } catch (e) {
    ElMessage.error('搜索失败')
  } finally {
    loading.value = false
  }
}

async function selectResult(r: MsdsResult) {
  selectedId.value = r.id
  // 通知右侧面板打开预览（预览显示在右侧大区域，不在左侧 accordion 内）
  emit('open-data-center-preview', { id: r.id, filename: r.filename, file_format: r.file_format })
  // 填充摘要字段
  summary.value = {
    id: r.id,
    filename: r.filename,
    product_name_cn: r.product_name_cn,
    physical_form: r.physical_form,
    ion_type: r.ion_type,
    ph: r.ph,
    file_format: r.file_format,
    file_path: r.file_path,
  }
  // 尝试从后端补充更完整的信息
  try {
    const res = await phase2Api.getDataCenterSummary(r.id)
    if (res.data) {
      summary.value = { ...summary.value, ...res.data }
    }
  } catch {
    // 已使用 r 的数据作为 fallback
  }
}

function downloadFile() {
  if (!selectedId.value) return
  const url = phase2Api.getDataCenterFileUrl(selectedId.value)
  const a = document.createElement('a')
  a.href = url
  a.download = summary.value.filename || 'msds'
  a.target = '_blank'
  a.click()
}

function onUploadFileSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  fileToUpload.value = file
  uploadFileName.value = file.name
}

async function confirmUpload() {
  if (!fileToUpload.value || !selectedId.value) return
  uploading.value = true
  try {
    await phase2Api.uploadCorrectedMsds(selectedId.value, fileToUpload.value)
    ElMessage.success('上传成功，文件已保存为时间戳版本')
    showUploadDialog.value = false
    fileToUpload.value = null
    uploadFileName.value = ''
    // 重新搜索以刷新列表
    await search()
  } catch {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.data-center-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

/* ── 搜索栏 ─────────────────────────────────────────── */
.search-bar {
  display: flex;
  gap: 8px;
  padding: 12px 12px 8px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.search-input {
  flex: 1;
  height: 32px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  padding: 0 10px;
  font-size: 13px;
  outline: none;
  background: var(--el-fill-color-light);
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.search-input:focus { border-color: var(--el-color-primary); background: #fff; }
.search-btn {
  height: 32px;
  padding: 0 14px;
  border: none;
  border-radius: 4px;
  background: var(--el-color-primary);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.15s;
}
.search-btn:hover:not(:disabled) { opacity: 0.85; }
.search-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── 结果列表 ─────────────────────────────────────────── */
.results-list {
  flex: 0 0 auto;
  max-height: 180px;
  overflow-y: auto;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.result-item {
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  transition: background 0.15s;
}
.result-item:last-child { border-bottom: none; }
.result-item:hover { background: var(--el-fill-color-light); }
.result-item--selected { background: var(--el-color-primary-light-9); }
.result-main {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}
.result-filename {
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.result-product {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.result-badge {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 600;
  flex-shrink: 0;
}
.result-badge.pdf { background: #f56c6c22; color: #f56c6c; }
.result-badge.doc { background: #409eff22; color: #409eff; }

/* ── 空状态 ─────────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}

/* ── 详情区 ─────────────────────────────────────────── */
.detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.detail-left {
  flex: 0 0 auto;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.field-row {
  display: grid;
  grid-template-columns: 80px 1fr;
  align-items: center;
  height: 36px;
  padding: 0 12px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  gap: 8px;
}
.field-row:last-child { border-bottom: none; }
.field-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.field-body { font-size: 12px; }
.field-body--readonly {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.action-row {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
}
.action-btn {
  flex: 1;
  height: 30px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-fill-color-light);
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.action-btn:hover { border-color: var(--el-color-primary); color: var(--el-color-primary); }
.action-btn--primary {
  background: var(--el-color-primary);
  color: #fff;
  border-color: var(--el-color-primary);
}
.action-btn--primary:hover { opacity: 0.85; color: #fff; }

/* ── 预览区 ─────────────────────────────────────────── */
.detail-right {
  flex: 1;
  overflow: hidden;
  background: #f5f5f5;
}
.pdf-iframe {
  width: 100%;
  height: 100%;
  min-height: 400px;
  border: none;
}
.doc-preview-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.doc-preview-hint em {
  font-style: normal;
  font-size: 11px;
  color: var(--el-text-color-placeholder);
}
.doc-preview-hint .action-btn { width: auto; padding: 0 20px; margin-top: 8px; }

/* ── 上传弹窗 ─────────────────────────────────────────── */
.upload-dialog-body { padding: 8px 0; }
.upload-hint { font-size: 13px; color: var(--el-text-color-secondary); margin-bottom: 16px; }
.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 90px;
  border: 1.5px dashed var(--el-border-color);
  border-radius: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}
.upload-zone:hover { border-color: var(--el-color-primary); color: var(--el-color-primary); }
.upload-zone em { font-style: normal; font-size: 11px; color: var(--el-text-color-placeholder); }
.upload-file-name {
  margin-top: 10px;
  font-size: 12px;
  color: var(--el-color-primary);
  text-align: center;
}
</style>