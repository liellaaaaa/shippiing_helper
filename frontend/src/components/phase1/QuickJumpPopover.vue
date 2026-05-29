<template>
  <el-popover
    placement="top"
    :width="200"
    trigger="click"
  >
    <template #reference>
      <el-button link type="primary" size="small">🔗</el-button>
    </template>
    <div class="popover-content">
      <p class="popover-title">选择检查目标</p>
      <el-button class="jump-btn" @click="goToOrder">
        📦 检查订单数据
      </el-button>
      <el-button class="jump-btn" @click="goToPI">
        📄 检查 PI 数据
      </el-button>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const props = defineProps<{
  internalCode: string
  orderId: number
  piContractId?: number
}>()

const router = useRouter()

const goToOrder = () => {
  router.push({
    path: '/order-paste',
    query: { orderId: String(props.orderId), highlight: props.internalCode }
  })
}

const goToPI = () => {
  router.push({
    path: '/pi-extract',
    query: { highlight: props.internalCode }
  })
}
</script>

<style scoped>
.popover-content { padding: 4px 0; }
.popover-title { font-size: 13px; color: #909399; margin: 0 0 8px 8px; }
.jump-btn { width: 100%; margin: 2px 0; justify-content: flex-start; }
</style>