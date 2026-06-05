<template>
  <el-drawer
    v-model="visible"
    title="我的模板"
    direction="rtl"
    size="400px"
    :append-to-body="true"
  >
    <div v-if="loading" class="loading-state">
      <span>加载中...</span>
    </div>

    <div v-else-if="!docs.length" class="empty-state">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".3">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
      </svg>
      <span>暂无已保存的模板</span>
      <span class="empty-hint">空白模板编辑后会保存在此</span>
    </div>

    <div v-else class="doc-list">
      <div
        v-for="doc in docs"
        :key="doc.doc_key"
        class="doc-item"
        @click="$emit('open-doc', doc)"
      >
        <div class="doc-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
        </div>
        <div class="doc-info">
          <div class="doc-name">{{ doc.file_name }}</div>
          <div class="doc-meta">
            <el-tag size="small" type="info">{{ doc.doc_type }}</el-tag>
            <span class="doc-time">{{ formatDate(doc.created_at) }}</span>
          </div>
        </div>
        <div class="doc-open">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { phase2Api } from '@/api/phase2'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'open-doc', doc: any): void }>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const docs = ref<any[]>([])
const loading = ref(false)

watch(visible, async (open) => {
  if (!open) return
  loading.value = true
  docs.value = []
  try {
    const res = await phase2Api.listMyTemplates()
    docs.value = res.data || []
  } finally {
    loading.value = false
  }
})

function formatDate(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}
</script>

<style scoped>
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 200px;
  color: var(--el-text-color-placeholder);
  font-size: 13px;
}
.empty-hint { font-size: 11px; color: var(--el-text-color-placeholder); }
.doc-list { display: flex; flex-direction: column; }
.doc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-extra-light);
  cursor: pointer;
  transition: background 0.15s;
}
.doc-item:hover { background: var(--el-fill-color-light); }
.doc-icon { color: var(--el-color-primary); flex-shrink: 0; }
.doc-info { flex: 1; min-width: 0; }
.doc-name { font-size: 13px; font-weight: 500; color: var(--el-text-color-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.doc-time { font-size: 11px; color: var(--el-text-color-placeholder); }
.doc-open { color: var(--el-text-color-placeholder); flex-shrink: 0; }
.doc-item:hover .doc-open { color: var(--el-color-primary); }
</style>