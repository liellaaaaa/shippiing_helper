<template>
  <div class="document-editor">
    <div v-if="!editorReady" class="editor-loading">
      <el-skeleton :rows="10" animated />
      <div class="loading-hint">正在连接文档服务器...</div>
    </div>
    <iframe
      v-show="editorReady"
      ref="iframeRef"
      :src="editorUrl"
      class="editor-iframe"
      frameborder="0"
      allowfullscreen
      @load="onIframeLoad"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  documentServerUrl: string
  docKey: string
  token: string
  downloadUrl: string
}>()

const editorReady = ref(false)
let loadingTimer: ReturnType<typeof setTimeout>

const editorUrl = computed(() => {
  const base = props.documentServerUrl.replace(/\/$/, '')
  return `${base}/apps/documenteditor/main.html?docKey=${props.docKey}&token=${props.token}&downloadUrl=${encodeURIComponent(props.downloadUrl)}`
})

function onIframeLoad() {
  editorReady.value = true
  clearTimeout(loadingTimer)
}

onMounted(() => {
  loadingTimer = setTimeout(() => {
    if (!editorReady.value) {
      ElMessage.error('文档服务器连接超时，请刷新重试')
    }
  }, 10000)
})

onUnmounted(() => {
  clearTimeout(loadingTimer)
})
</script>

<style scoped>
.document-editor { width: 100%; height: 100%; position: relative; }
.editor-iframe { width: 100%; height: 100%; min-height: 600px; }
.editor-loading { padding: 24px; }
.loading-hint { text-align: center; color: #999; margin-top: 16px; font-size: 14px; }
</style>