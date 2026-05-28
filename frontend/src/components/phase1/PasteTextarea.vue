<template>
  <div class="paste-textarea">
    <el-input
      v-model="text"
      type="textarea"
      :rows="10"
      :placeholder="placeholder"
      resize="vertical"
      @paste="handlePaste"
    />
    <div class="actions">
      <el-button type="primary" :disabled="!text.trim()" @click="handleParse">
        解析
      </el-button>
      <el-button @click="handleClear" :disabled="!text.trim()">
        清空
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  modelValue?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'parse': [text: string]
  'clear': []
}>()

const text = ref(props.modelValue ?? '')
const placeholder = `将 Excel/Spreadsheet 订单数据粘贴到此处
（支持 Tab 分隔或换行分隔）
示例：
订单号\t客户编号\t内部编号\t产品中文名\t规格kg\t订单量kg
HT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂\t25\t2400`

function handlePaste() {
  // 延迟以确保剪贴板数据已填充
  setTimeout(() => {
    emit('update:modelValue', text.value)
  }, 0)
}

function handleParse() {
  if (!text.value.trim()) return
  emit('parse', text.value)
}

function handleClear() {
  text.value = ''
  emit('update:modelValue', '')
  emit('clear')
}

watch(() => props.modelValue, (val) => {
  if (val !== text.value) text.value = val ?? ''
})
</script>

<style scoped>
.paste-textarea {
  width: 100%;
}
.paste-textarea :deep(.el-textarea__inner) {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
}
.actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
</style>