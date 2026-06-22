<template>
  <div class="field-ref-card">
    <!-- 搜索框 -->
    <div class="ref-search">
      <input
        v-model="searchQuery"
        class="ref-search-input"
        placeholder="搜索运输鉴定报告（品名/报关名）"
        @keyup.enter="doSearch"
      />
      <button class="ref-search-btn" @click="doSearch" :disabled="searching">
        <span v-if="!searching">🔍</span>
        <span v-else>...</span>
      </button>
    </div>

    <!-- 搜索结果列表 -->
    <div v-if="searchResults.length > 0" class="ref-results">
      <div class="ref-results-header">搜索结果（{{ searchResults.length }}）</div>
      <div
        v-for="r in searchResults"
        :key="r.id"
        class="ref-result-item"
        :class="{ linked: isLinked(r.id) }"
        @click="addReport(r)"
        :title="isLinked(r.id) ? '已关联，可追加' : '点击添加'"
      >
        <div class="ref-result-main">
          <span class="ref-result-cn">{{ r.product_name_cn || '—' }}</span>
          <span class="ref-result-en">{{ r.product_name_en || '' }}</span>
        </div>
        <div class="ref-result-sub">
          <span class="ref-result-no">{{ r.report_no }}</span>
          <span v-if="isLinked(r.id)" class="ref-result-badge">已关联</span>
        </div>
      </div>
    </div>

    <div v-if="searchDone && searchResults.length === 0 && searchQuery" class="ref-empty">
      <span>无匹配结果</span>
    </div>

    <!-- 已关联的鉴定报告列表 -->
    <div v-if="linkedReports.length > 0" class="linked-section">
      <div class="linked-section-header">
        <span>已选报告</span>
        <span class="linked-count">{{ linkedReports.length }}</span>
      </div>
      <div
        v-for="(report, idx) in linkedReports"
        :key="report.link_id"
        class="linked-report-card"
      >
        <div class="linked-report-header">
          <span class="linked-report-num">Report {{ idx + 1 }}</span>
          <button class="linked-report-remove" @click="removeReport(idx)" title="移除">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="linked-report-fields">
          <div class="lr-field">
            <span class="lr-field-label">报告编号</span>
            <span class="lr-field-value" :title="report.report_no">{{ report.report_no || '—' }}</span>
            <button class="lr-copy" @click="copy(report.report_no)" title="复制">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>
          <div class="lr-field">
            <span class="lr-field-label">品名中文</span>
            <span class="lr-field-value" :title="report.product_name_cn">{{ report.product_name_cn || '—' }}</span>
            <button class="lr-copy" @click="copy(report.product_name_cn)" title="复制">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>
          <div class="lr-field">
            <span class="lr-field-label">品名英文</span>
            <span class="lr-field-value" :title="report.product_name_en">{{ report.product_name_en || '—' }}</span>
            <button class="lr-copy" @click="copy(report.product_name_en)" title="复制">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>
          <div class="lr-field">
            <span class="lr-field-label">样品描述(中)</span>
            <span class="lr-field-value" :title="report.sample_desc_cn">{{ report.sample_desc_cn || '—' }}</span>
            <button class="lr-copy" @click="copy(report.sample_desc_cn)" title="复制">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>
          <div class="lr-field">
            <span class="lr-field-label">样品描述(英)</span>
            <span class="lr-field-value" :title="report.sample_desc_en">{{ report.sample_desc_en || '—' }}</span>
            <button class="lr-copy" @click="copy(report.sample_desc_en)" title="复制">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 初始空状态 -->
    <div v-if="!searchDone && !searchResults.length" class="ref-init">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".3">
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="13 2 13 8 20 8"/>
      </svg>
      <span>搜索运输鉴定报告，提取字段用于制作MSDS</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { phase2Api } from '@/api/phase2'

// ─── Types ───────────────────────────────────────────────────────────────────
interface TransportReportSearchItem {
  id: number
  filename: string
  report_no: string
  product_name_cn: string
  product_name_en: string
  sample_desc_cn: string
  sample_desc_en: string
}

interface LinkedReport {
  id: number
  filename: string
  report_no: string
  product_name_cn: string
  product_name_en: string
  sample_desc_cn: string
  sample_desc_en: string
}

// ─── State ───────────────────────────────────────────────────────────────────
const searchQuery = ref('')
const searching = ref(false)
const searchDone = ref(false)
const searchResults = ref<TransportReportSearchItem[]>([])
const linkedReports = ref<LinkedReport[]>([])

// ─── Search ───────────────────────────────────────────────────────────────────
async function doSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  searchDone.value = false
  searchResults.value = []
  try {
    const res = await phase2Api.searchTransportReportsByName(searchQuery.value)
    searchResults.value = res.data?.items || []
  } catch {
    searchResults.value = []
  } finally {
    searching.value = false
    searchDone.value = true
  }
}

// ─── Add / Remove ─────────────────────────────────────────────────────────────
function isLinked(reportId: number): boolean {
  return linkedReports.value.some(r => r.id === reportId)
}

function addReport(report: TransportReportSearchItem) {
  if (isLinked(report.id)) {
    ElMessage.info('已添加，可继续追加其他报告')
    return
  }
  linkedReports.value.push({ ...report })
  searchQuery.value = ''
  searchResults.value = []
  searchDone.value = false
}

function removeReport(index: number) {
  linkedReports.value.splice(index, 1)
}

// ─── Copy ────────────────────────────────────────────────────────────────────
async function copy(text: string) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败')
  }
}
</script>

<style scoped>
.field-ref-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

/* ── Current Item ─────────────────────────────────────────── */
.current-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-extra-light);
  flex-shrink: 0;
}
.current-item--active {
  background: var(--el-color-primary-light-9);
  border-bottom-color: var(--el-color-primary-light-7);
}
.current-item--empty {
  background: #fff8e6;
  border-bottom-color: #ffe6b0;
  cursor: pointer;
  transition: background 0.15s;
}
.current-item--empty:hover { background: #fff3cc; }
.current-item-label {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
  flex-shrink: 0;
}
.current-item-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.current-item-code {
  font-size: 10px;
  color: var(--el-color-info-light-3);
  font-family: 'JetBrains Mono', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.current-item-hint {
  margin-left: auto;
  font-size: 10px;
  color: var(--el-color-warning, #e6a23c);
  white-space: nowrap;
}
.muted { color: var(--el-text-color-placeholder); font-weight: 400; }

/* ── Search ─────────────────────────────────────────────── */
.ref-search {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  flex-shrink: 0;
}
.ref-search-input {
  flex: 1;
  height: 28px;
  border: 1px solid var(--el-border-color, #dcdfe6);
  border-radius: 4px;
  padding: 0 8px;
  font-size: 12px;
  background: var(--el-fill-color-light, #f5f7fa);
  outline: none;
  transition: border-color 0.2s;
  min-width: 0;
}
.ref-search-input:focus { border-color: var(--el-color-primary, #409eff); background: #fff; }
.ref-search-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 4px;
  background: var(--el-color-primary-light-9, #ecf5ff);
  cursor: pointer;
  font-size: 12px;
  flex-shrink: 0;
  transition: opacity 0.15s;
}
.ref-search-btn:hover:not(:disabled) { opacity: 0.75; }
.ref-search-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Search Results ─────────────────────────────────────── */
.ref-results {
  flex-shrink: 0;
  max-height: 140px;
  overflow-y: auto;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.ref-results-header {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  padding: 4px 12px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.ref-result-item {
  padding: 6px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  transition: background 0.12s;
}
.ref-result-item:last-child { border-bottom: none; }
.ref-result-item:hover { background: var(--el-fill-color-light, #f5f7fa); }
.ref-result-item.linked { opacity: 0.65; }
.ref-result-main {
  display: flex;
  gap: 6px;
  align-items: baseline;
  margin-bottom: 2px;
}
.ref-result-cn {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}
.ref-result-en {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ref-result-sub {
  display: flex;
  gap: 6px;
  align-items: center;
}
.ref-result-no {
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--el-color-info);
}
.ref-result-badge {
  font-size: 9px;
  background: var(--el-color-success-light-9, #e8f5e9);
  color: var(--el-color-success, #67c23a);
  padding: 1px 4px;
  border-radius: 3px;
}

/* ── Empty ─────────────────────────────────────────────── */
.ref-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  color: var(--el-text-color-placeholder, #c0c4cc);
  font-size: 11px;
  flex-shrink: 0;
}

/* ── Linked Reports ──────────────────────────────────────── */
.linked-section {
  flex: 1;
  overflow-y: auto;
}
.linked-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-extra-light);
  font-size: 11px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}
.linked-count {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 10px;
}

.linked-report-card {
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.linked-report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.linked-report-num {
  font-size: 11px;
  font-weight: 600;
  color: var(--el-color-primary);
}
.linked-report-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--el-text-color-placeholder);
  cursor: pointer;
  border-radius: 3px;
  transition: color 0.15s, background 0.15s;
}
.linked-report-remove:hover {
  color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}

.linked-report-fields {
  display: flex;
  flex-direction: column;
}
.lr-field {
  display: grid;
  grid-template-columns: 80px 1fr 22px;
  align-items: center;
  gap: 4px;
  padding: 0 12px;
  height: 30px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
}
.lr-field:last-child { border-bottom: none; }
.lr-field-label {
  font-size: 10px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lr-field-value {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lr-copy {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--el-text-color-placeholder);
  cursor: pointer;
  border-radius: 3px;
  transition: color 0.15s, background 0.15s;
}
.lr-copy:hover {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

/* ── Init ───────────────────────────────────────────────── */
.ref-init {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 20px 12px;
  color: var(--el-text-color-placeholder, #c0c4cc);
  font-size: 11px;
  text-align: center;
  flex-shrink: 0;
}
.ref-init span { max-width: 160px; line-height: 1.4; }
</style>
