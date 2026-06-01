<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import ReferencePanel from './components/ReferencePanel.vue'
import DocumentEditor from './components/DocumentEditor.vue'
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
const currentPiNoOptions = computed(() => piList.value.map(p => p.pi_no))

// Auto-fill from route query
if (route.query.orderId) {
  selectedOrderId.value = Number(route.query.orderId)
}

const currentProductName = computed(() => currentOrderItems.value[0]?.product_cn || '')
const currentInternalCode = computed(() => currentOrderItems.value[0]?.internal_code || '')

async function loadOrderList() {
  const res = await fetch('/api/v1/merge/orders?tab=completed&page_size=100')
  const data = await res.json()
  orderList.value = data.orders || []
}

async function onOrderChange(orderId: number) {
  const res = await fetch(`/api/v1/merge/orders/${orderId}/comparison`)
  const data = await res.json()
  currentOrderItems.value = data.items || []
  // auto-select order-level pi_no as default for LOI
  if (data.pi_no) {
    selectedPiNo.value = data.pi_no
  }
}

async function openDocument(type: 'booking' | 'loi') {
  try {
    let res: any
    if (type === 'booking') {
      res = await phase2Api.generateBooking(selectedOrderId.value!)
    } else {
      res = await phase2Api.generateLoi(selectedOrderId.value!, selectedPiNo.value)
    }
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

function downloadCurrentDoc() {
  if (!currentDocKey.value) return
  window.open(`/api/v1/onlyoffice/download/${currentDocKey.value}`, '_blank')
}

onMounted(() => {
  loadOrderList()
  if (selectedOrderId.value) {
    onOrderChange(selectedOrderId.value)
  }
})
</script>

<template>
  <div class="phase2-workflow">
    <!-- Toolbar -->
    <div class="toolbar">
      <el-select v-model="selectedOrderId" placeholder="选择订单" @change="onOrderChange">
        <el-option v-for="o in orderList" :key="o.id" :label="`${o.order_no} - ${o.customer_code}`" :value="o.id" />
      </el-select>

      <el-select v-model="selectedPiNo" placeholder="选择PI合同" :disabled="!selectedOrderId">
        <el-option v-for="p in piList" :key="p.pi_no" :label="p.pi_no" :value="p.pi_no" />
      </el-select>

      <div class="doc-buttons">
        <el-button type="primary" :disabled="!selectedOrderId" @click="openDocument('booking')">订舱单</el-button>
        <el-button type="primary" :disabled="!selectedOrderId || !selectedPiNo" @click="openDocument('loi')">LOI保函</el-button>
        <el-button type="primary" @click="showMsdsDialog = true">MSDS</el-button>
      </div>
    </div>

    <!-- Main content -->
    <div class="main-content">
      <div class="left-panel">
        <ReferencePanel
          :order-id="selectedOrderId"
          :product-name="currentProductName"
          :internal-code="currentInternalCode"
        />
      </div>
      <div class="right-panel">
        <div v-if="!currentDocKey" class="editor-placeholder">
          <el-empty description="点击上方按钮加载文档" />
        </div>
        <DocumentEditor
          v-else
          :document-server-url="currentConfig.documentServerUrl"
          :doc-key="currentDocKey"
          :token="currentConfig.token"
          :download-url="currentConfig.downloadUrl"
        />
      </div>
    </div>

    <!-- Bottom bar -->
    <div class="bottom-bar">
      <el-button @click="downloadCurrentDoc">下载</el-button>
    </div>

    <!-- MSDS product select dialog -->
    <el-dialog v-model="showMsdsDialog" title="选择产品生成MSDS" width="400px">
      <el-select v-model="selectedProductForMsds" placeholder="选择产品" style="width: 100%">
        <el-option v-for="item in currentOrderItems" :key="item.internal_code" :label="item.product_cn" :value="item.product_cn" />
      </el-select>
      <template #footer>
        <el-button @click="showMsdsDialog = false">取消</el-button>
        <el-button type="primary" @click="generateMsds">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.phase2-workflow { display: flex; flex-direction: column; height: 100vh; }
.toolbar { display: flex; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--el-border-color); align-items: center; }
.doc-buttons { display: flex; gap: 8px; }
.main-content { display: flex; flex: 1; overflow: hidden; }
.left-panel { width: 35%; border-right: 1px solid var(--el-border-color); overflow-y: auto; }
.right-panel { width: 65%; overflow: hidden; display: flex; flex-direction: column; }
.editor-placeholder { display: flex; align-items: center; justify-content: center; flex: 1; }
.bottom-bar { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--el-border-color); }
</style>