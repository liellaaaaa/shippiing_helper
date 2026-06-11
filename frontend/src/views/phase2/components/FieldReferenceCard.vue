<template>
  <div class="field-ref-card">
    <!-- 文档类型切换 -->
    <div class="ref-tabs">
      <button
        v-for="t in docTypes"
        :key="t.value"
        class="ref-tab"
        :class="{ active: selectedType === t.value }"
        @click="selectedType = t.value; clearSelection()"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- 搜索框 -->
    <div class="ref-search">
      <input
        v-model="searchQuery"
        class="ref-search-input"
        :placeholder="selectedType === 'msds' ? '搜索MSDS，如 吸湿排汗' : '搜索运输鉴定报告'"
        @keyup.enter="doSearch"
      />
      <button class="ref-search-btn" @click="doSearch" :disabled="searching">
        <span v-if="!searching">🔍</span>
        <span v-else>...</span>
      </button>
    </div>

    <!-- MSDS 搜索结果列表 -->
    <div v-if="selectedType === 'msds' && results.length" class="ref-results">
      <div
        v-for="r in results"
        :key="r.id"
        class="ref-result-item"
        :class="{ selected: selectedId === r.id }"
        @click="selectResult(r)"
      >
        <span class="ref-result-name">{{ r.filename }}</span>
      </div>
    </div>

    <!-- 运输鉴定报告搜索结果列表 -->
    <div v-if="selectedType === 'transport' && results.length" class="ref-results">
      <div
        v-for="r in results"
        :key="r.id"
        class="ref-result-item"
        :class="{ selected: selectedId === r.id }"
        @click="selectResult(r)"
      >
        <span class="ref-result-name">{{ r.filename }}</span>
      </div>
    </div>

    <!-- 无搜索结果显示空状态提示 -->
    <div v-if="!searching && searchDone && !results.length" class="ref-empty">
      <span>无匹配结果</span>
    </div>

    <!-- 选中后的字段展示区 -->
    <div v-if="selectedRecord" class="ref-fields">
      <div class="ref-fields-header">
        <span>{{ selectedRecord.filename || selectedRecord.product_name_cn }}</span>
        <button class="ref-copy-all" @click="copyAllFields" title="复制所有字段">📋</button>
      </div>
      <div class="ref-field-list">
        <div v-for="f in displayFields" :key="f.key" class="ref-field-row">
          <span class="ref-field-label">{{ f.label }}</span>
          <span class="ref-field-value" :title="String(f.value)">{{ f.value || '—' }}</span>
          <button class="ref-field-copy" @click="copy(f.value)" title="复制">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 初始空状态 -->
    <div v-if="!selectedRecord && !searchDone" class="ref-init">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".3">
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="13 2 13 8 20 8"/>
      </svg>
      <span>搜索MSDS或运输鉴定报告，提取字段复制到文档</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { phase2Api } from '@/api/phase2'

interface MSDSResult {
  id: number
  filename: string
  product_name_cn: string
  physical_form: string
  ion_type: string
  ph: string
}

interface TransportResult {
  id: number
  filename: string
  report_no: string
  sample_description: string
}

interface DisplayField {
  key: string
  label: string
  value: string
}

const docTypes = [
  { value: 'msds' as const, label: 'MSDS' },
  { value: 'transport' as const, label: '运输鉴定报告' },
]

const selectedType = ref<'msds' | 'transport'>('msds')
const searchQuery = ref('')
const searching = ref(false)
const searchDone = ref(false)
const results = ref<(MSDSResult | TransportResult)[]>([])
const selectedId = ref<number | null>(null)
const selectedRecord = ref<any | null>(null)

const displayFields = computed<DisplayField[]>(() => {
  if (!selectedRecord.value) return []
  if (selectedType.value === 'msds') {
    const r = selectedRecord.value as MSDSResult
    return [
      { key: 'product_name_cn', label: '产品名称', value: r.product_name_cn || '' },
      { key: 'physical_form', label: '外观与性状', value: r.physical_form || '' },
      { key: 'ion_type', label: '离子型', value: r.ion_type || '' },
      { key: 'ph', label: 'pH值', value: r.ph || '' },
    ]
  } else {
    const r = selectedRecord.value as TransportResult
    return [
      { key: 'report_no', label: '报告编号', value: r.report_no || '' },
      { key: 'sample_description', label: '样品名称', value: r.sample_description || '' },
    ]
  }
})

async function doSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  searchDone.value = false
  results.value = []
  selectedRecord.value = null
  selectedId.value = null
  try {
    if (selectedType.value === 'msds') {
      const res = await phase2Api.listMsds({ search: searchQuery.value, pageSize: 20 })
      results.value = res.data.items || []
    } else {
      const res = await phase2Api.searchTransportReports(searchQuery.value)
      results.value = res.data.items || []
    }
  } catch {
    results.value = []
  } finally {
    searching.value = false
    searchDone.value = true
  }
}

async function selectResult(r: MSDSResult | TransportResult) {
  selectedId.value = r.id
  selectedRecord.value = r
}

function clearSelection() {
  results.value = []
  selectedRecord.value = null
  selectedId.value = null
  searchQuery.value = ''
  searchDone.value = false
}

async function copy(text: string) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败')
  }
}

async function copyAllFields() {
  const text = displayFields.value
    .map(f => `${f.label}: ${f.value}`)
    .filter(f => f.includes(': '))
    .join('\n')
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制所有字段')
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
  overflow: hidden;
}

/* ── Tabs ─────────────────────────────────────────────── */
.ref-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--el-border-color-light, #e4e7ed);
  padding: 0 12px;
  flex-shrink: 0;
}
.ref-tab {
  padding: 8px 14px;
  border: none;
  background: transparent;
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}
.ref-tab:hover { color: var(--el-color-primary, #409eff); }
.ref-tab.active {
  color: var(--el-color-primary, #409eff);
  border-bottom-color: var(--el-color-primary, #409eff);
  font-weight: 600;
}

/* ── Search ─────────────────────────────────────────────── */
.ref-search {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-extra-light, #f2f6fc);
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

/* ── Results list ───────────────────────────────────────────── */
.ref-results {
  flex-shrink: 0;
  max-height: 120px;
  overflow-y: auto;
  border-bottom: 1px solid var(--el-border-color-extra-light, #f2f6fc);
}
.ref-result-item {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-extra-light, #f2f6fc);
  transition: background 0.12s;
  gap: 6px;
}
.ref-result-item:last-child { border-bottom: none; }
.ref-result-item:hover { background: var(--el-fill-color-light, #f5f7fa); }
.ref-result-item.selected { background: var(--el-color-primary-light-9, #ecf5ff); }
.ref-result-name {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--el-text-color-primary, #303133);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Empty / Init ───────────────────────────────────────── */
.ref-empty, .ref-init {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 16px 12px;
  color: var(--el-text-color-placeholder, #c0c4cc);
  font-size: 11px;
  text-align: center;
  flex-shrink: 0;
}
.ref-init span { max-width: 160px; line-height: 1.4; }

/* ── Fields display ───────────────────────────────────────── */
.ref-fields {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.ref-fields-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  background: var(--el-fill-color-lighter, #f5f7fa);
  border-bottom: 1px solid var(--el-border-color-extra-light, #f2f6fc);
  font-size: 11px;
  color: var(--el-text-color-secondary, #909399);
  font-weight: 500;
  gap: 8px;
  flex-shrink: 0;
}
.ref-fields-header span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ref-copy-all {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  flex-shrink: 0;
  padding: 2px 4px;
  border-radius: 3px;
  transition: background 0.15s;
}
.ref-copy-all:hover { background: var(--el-fill-color, #f5f7fa); }

.ref-field-list {
  display: flex;
  flex-direction: column;
}
.ref-field-row {
  display: grid;
  grid-template-columns: 80px 1fr 26px;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  height: 34px;
  border-bottom: 1px solid var(--el-border-color-extra-light, #f2f6fc);
}
.ref-field-row:last-child { border-bottom: none; }
.ref-field-label {
  font-size: 11px;
  color: var(--el-text-color-secondary, #909399);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ref-field-value {
  font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--el-text-color-primary, #303133);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ref-field-copy {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--el-text-color-placeholder, #c0c4cc);
  cursor: pointer;
  border-radius: 3px;
  flex-shrink: 0;
  transition: color 0.15s, background 0.15s;
}
.ref-field-copy:hover {
  color: var(--el-color-primary, #409eff);
  background: var(--el-color-primary-light-9, #ecf5ff);
}
</style>
