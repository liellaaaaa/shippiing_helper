<template>
  <div class="order-paste-page">
    <el-page-header @back="handleBack" content="订单粘贴解析" />

    <div class="page-content">
      <PasteTextarea
        v-model="rawText"
        @parse="handleParse"
        @clear="handleClear"
      />

      <div v-if="parseResult" class="preview-section">
        <OrderPreviewForm
          :parse-result="parseResult"
          @save="handleSave"
          @reset="handleReset"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PasteTextarea from '@/components/phase1/PasteTextarea.vue'
import OrderPreviewForm from '@/components/phase1/OrderPreviewForm.vue'
import { ordersApi, type PasteParseResponse, type ParsedOrderSchema } from '@/api/orders'

const router = useRouter()
const rawText = ref('')
const parseResult = ref<PasteParseResponse | null>(null)

async function handleParse(text: string) {
  try {
    parseResult.value = await ordersApi.parsePaste(text)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? '解析失败，请检查数据格式')
  }
}

async function handleSave(orders: ParsedOrderSchema[]) {
  try {
    for (const order of orders) {
      await ordersApi.saveOrder(order)
    }
    ElMessage.success('保存成功')
    handleReset()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? '保存失败')
  }
}

function handleReset() {
  rawText.value = ''
  parseResult.value = null
}

function handleClear() {
  handleReset()
}

function handleBack() {
  router.back()
}
</script>

<style scoped>
.order-paste-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}
.page-content {
  margin-top: 24px;
}
.preview-section {
  margin-top: 24px;
}
</style>