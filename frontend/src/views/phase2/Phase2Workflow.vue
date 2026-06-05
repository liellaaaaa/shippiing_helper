<template>
  <div class="phase2">

    <!-- ── Toolbar ─────────────────────────────── -->
    <header class="toolbar">
      <div class="toolbar-left">
        <svg class="toolbar-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        <span class="toolbar-title">文档编辑</span>
      </div>

      <div class="toolbar-center">
        <div class="toolbar-field">
          <label class="toolbar-label">订单</label>
          <el-select
            v-model="selectedOrderId"
            placeholder="选择订单"
            size="small"
            class="toolbar-select"
            @change="onOrderChange"
            clearable
          >
            <template #empty>
              <span class="empty-hint">无已确认订单</span>
            </template>
            <el-option
              v-for="o in orderList"
              :key="o.id"
              :label="`${o.order_no} · ${o.customer_code}`"
              :value="o.id"
            />
          </el-select>
        </div>

        <div class="toolbar-field" v-if="selectedOrderId">
          <label class="toolbar-label">PI合同</label>
          <el-select
            v-model="selectedPiNo"
            placeholder="选择PI"
            size="small"
            class="toolbar-select"
            clearable
          >
            <el-option
              v-for="p in piList"
              :key="p.pi_no"
              :label="p.pi_no"
              :value="p.pi_no"
            />
          </el-select>
        </div>
      </div>

      <div class="toolbar-actions">
        <el-button
          type="primary"
          size="small"
          :disabled="!selectedOrderId"
          @click="openDocument('booking')"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
            <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
          </svg>
          订舱单
        </el-button>
        <el-button
          type="primary"
          size="small"
          :disabled="!selectedOrderId || !selectedPiNo"
          @click="openDocument('loi')"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
            <path d="M14 2H6a2 2 0 0 1 2v20a2 2 0 0 1-2 2H18a2 2 0 0 1-2-2V8l4-4z"/><path d="M14 2v6h6M16 13l4-4 4 4"/>
          </svg>
          LOI保函
        </el-button>
        <el-button size="small" @click="showMsdsDialog = true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M8 13h8M8 17h8M8 9h2"/>
          </svg>
          MSDS
        </el-button>
        <el-dropdown @command="(cmd: 'booking' | 'loi' | 'msds') => openBlankTemplate(cmd)" trigger="click">
          <el-button size="small">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
              <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>
            </svg>
            空白模板
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="booking">📄 订舱单 Booking</el-dropdown-item>
              <el-dropdown-item command="loi">📝 LOI保函</el-dropdown-item>
              <el-dropdown-item command="msds">⚠️ MSDS物质安全表</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button size="small" @click="showMyDocuments = true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          我的模板
        </el-button>
      </div>
    </header>

    <!-- ── Main ──────────────────────────────── -->
    <div class="main">
      <!-- Left: Reference Panel -->
      <aside class="ref-panel">
        <ReferencePanel :order-id="selectedOrderId" />
      </aside>

      <!-- Right: Document Editor -->
      <main class="editor-panel">
        <div v-if="!currentDocKey" class="editor-empty">
          <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity=".25">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="20" y2="17"/><line x1="20" y1="13" x2="16" y2="17"/>
          </svg>
          <p class="empty-title">点击上方按钮生成文档</p>
          <p class="empty-sub">订舱单 / LOI保函 / MSDS</p>
        </div>
        <DocumentEditor
          v-else
          :key="currentDocKey"
          :document-server-url="currentConfig.documentServerUrl"
          :doc-key="currentDocKey"
          :token="currentConfig.token"
          :download-url="currentConfig.downloadUrl"
        />
        <MyDocumentsDrawer v-model="showMyDocuments" @open-doc="onOpenMyDoc" />
      </main>
    </div>

    <!-- ── MSDS Dialog ──────────────────────────── -->
    <el-dialog
      v-model="showMsdsDialog"
      title="生成 MSDS"
      width="440px"
      :append-to-body="true"
      class="msds-dialog"
    >
      <div class="msds-select-row">
        <label class="msds-label">选择产品</label>
        <el-select
          v-model="selectedProductForMsds"
          placeholder="从当前订单选择产品"
          size="default"
          class="msds-select"
          clearable
        >
          <el-option
            v-for="item in currentOrderItems"
            :key="item.internal_code"
            :label="item.product_cn"
            :value="item.product_cn"
          />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="showMsdsDialog = false">取消</el-button>
        <el-button type="primary" @click="generateMsds" :disabled="!selectedProductForMsds">
          生成文档
        </el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import ReferencePanel from './components/ReferencePanel.vue'
import DocumentEditor from './components/DocumentEditor.vue'
import MyDocumentsDrawer from './components/MyDocumentsDrawer.vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { phase2Api } from '@/api/phase2'

const route = useRoute()

const selectedOrderId = ref<number | null>(null)
const selectedPiNo = ref<string>('')
const orderList = ref<any[]>([])
const piList = ref<any[]>([])
const currentOrderItems = ref<any[]>([])
const currentDocKey = ref('')
const currentConfig = ref<any>({})
const showMsdsDialog = ref(false)
const selectedProductForMsds = ref('')
const showMyDocuments = ref(false)

// Auto-fill from route query
if (route.query.orderId) {
  selectedOrderId.value = Number(route.query.orderId)
}

async function loadOrderList() {
  const res = await fetch('/api/v1/merge/orders?tab=completed&page_size=100')
  const data = await res.json()
  orderList.value = data.orders || []
}

async function onOrderChange(orderId: number) {
  selectedPiNo.value = ''
  const res = await fetch(`/api/v1/merge/orders/${orderId}/comparison`)
  const data = await res.json()
  currentOrderItems.value = data.items || []
  if (data.pi_no) selectedPiNo.value = data.pi_no
  piList.value = []
}

async function openBlankTemplate(type: 'booking' | 'loi' | 'msds') {
  try {
    const res = await phase2Api.openBlankTemplate(type)
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('模板打开失败: ' + (e.message || ''))
  }
}

function onOpenMyDoc(doc: any) {
  showMyDocuments.value = false
  currentDocKey.value = doc.doc_key
  currentConfig.value = {
    token: doc.token,
    documentServerUrl: currentConfig.value.documentServerUrl,
    documentKey: doc.doc_key,
    downloadUrl: `/api/v1/onlyoffice/download/${doc.doc_key}`,
  }
}

async function openDocument(type: 'booking' | 'loi') {
  try {
    const res = type === 'booking'
      ? await phase2Api.generateBooking(selectedOrderId.value!)
      : await phase2Api.generateLoi(selectedOrderId.value!, selectedPiNo.value)
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('文档生成失败: ' + (e.message || ''))
  }
}

async function generateMsds() {
  if (!selectedProductForMsds.value) return
  showMsdsDialog.value = false
  try {
    const res = await phase2Api.generateMsds(selectedProductForMsds.value)
    currentDocKey.value = res.data.documentKey || res.data.docKey
    currentConfig.value = res.data
  } catch (e: any) {
    ElMessage.error('MSDS生成失败: ' + (e.message || ''))
  }
}

onMounted(() => {
  loadOrderList()
  if (selectedOrderId.value) onOrderChange(selectedOrderId.value)
})
</script>

<style scoped>
/* ── Root ─────────────────────────────────────── */
.phase2 {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--el-bg-color-page, #f5f7fa);
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

/* ── Toolbar ─────────────────────────────────── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 56px;
  padding: 0 20px;
  background: var(--el-fill-color-lighter, #f5f7fa);
  border-bottom: 1px solid var(--el-border-color-light, #e4e7ed);
  flex-shrink: 0;
  box-shadow: 0 1px 0 var(--el-border-color-extralight);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-primary, #303133);
  min-width: 100px;
}
.toolbar-icon { color: var(--el-color-primary, #409eff); flex-shrink: 0; }
.toolbar-title { font-size: 14px; font-weight: 600; letter-spacing: 0.02em; }

.toolbar-center {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.toolbar-field {
  display: flex;
  align-items: center;
  gap: 6px;
}
.toolbar-label {
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
  white-space: nowrap;
}
.toolbar-select { width: 200px; }

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* ── Main ──────────────────────────────────── */
.main {
  display: grid;
  grid-template-columns: 340px 1fr;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.ref-panel {
  overflow-y: auto;
  border-right: 1px solid var(--el-border-color-light, #e4e7ed);
  background: var(--el-fill-color, #fff);
}

.editor-panel {
  overflow: hidden;
  position: relative;
  background: var(--el-fill-color-lighter, #f5f7fa);
}

.editor-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--el-text-color-placeholder, #c0c4cc);
}
.empty-title {
  font-size: 15px;
  margin: 0;
  color: var(--el-text-color-secondary, #606266);
}
.empty-sub {
  font-size: 12px;
  margin: 0;
  color: var(--el-text-color-placeholder, #c0c4cc);
}

/* ── MSDS Dialog ────────────────────────────── */
.msds-select-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}
.msds-label {
  font-size: 13px;
  color: var(--el-text-color-regular, #606266);
  white-space: nowrap;
  min-width: 64px;
}
.msds-select { flex: 1; }
</style>
