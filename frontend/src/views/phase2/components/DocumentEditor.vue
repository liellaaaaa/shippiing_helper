<template>
  <div class="document-editor">
    <!-- 骨架屏始终渲染，确保 DOM 节点存在 -->
    <div class="editor-loading">
      <el-skeleton :rows="10" animated />
      <div class="loading-hint">正在连接文档服务器...</div>
    </div>
    <!-- OnlyOffice 编辑器挂载点（始终存在于 DOM，v-show 控制显示 -->
    <div ref="editorRef" id="onlyoffice-editor" class="editor-mount" style="display:none" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  documentServerUrl: string
  docKey: string
  token: string
  downloadUrl: string
  url?: string       // OnlyOffice 可访问的 URL（host.docker.internal:8000）
  docType?: string  // "cell" | "word" | "slide"
}>()

const editorRef = ref<HTMLElement | null>(null)
let docEditor: any = null
let loadingTimer: ReturnType<typeof setTimeout> | null = null

function getDocType(fileType: string | undefined): string {
  if (fileType === 'xlsx' || fileType === 'xls') return 'cell'
  if (fileType === 'docx' || fileType === 'doc') return 'word'
  if (fileType === 'pptx' || fileType === 'ppt') return 'slide'
  return props.docType || 'cell'
}

function buildConfig() {
  const dt = getDocType(props.docType)
  const ext = dt === 'cell' ? 'xlsx' : dt === 'word' ? 'docx' : 'pptx'
  const docUrl = props.url || props.downloadUrl
  console.log('[OnlyOffice] docType:', dt, 'docUrl:', docUrl, 'docKey:', props.docKey)
  return {
    document: {
      fileType: ext,
      key: props.docKey,
      title: `Document.${ext}`,
      url: docUrl,
    },
    documentType: dt,
    editorConfig: {
      callbackUrl: `http://host.docker.internal:8000/api/v1/onlyoffice/callback?doc_key=${props.docKey}`,
      mode: 'edit',
    },
  }
}

function loadOnlyOfficeAPI(): Promise<void> {
  return new Promise((resolve, reject) => {
    if ((window as any).DocsAPI) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = `${props.documentServerUrl}/web-apps/apps/api/documents/api.js`
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('OnlyOffice API 加载失败'))
    document.head.appendChild(script)
  })
}

async function mountEditor() {
  if (!editorRef.value) return
  try {
    // 显示骨架屏，隐藏编辑器
    const el = editorRef.value
    el.style.display = 'block'
    el.innerHTML = ''

    await loadOnlyOfficeAPI()
    const DocsAPI = (window as any).DocsAPI
    if (!DocsAPI) throw new Error('DocsAPI 未定义')

    const config = buildConfig()
    docEditor = new DocsAPI.DocEditor(el.id, config)
  } catch (e: any) {
    ElMessage.error('文档服务器连接失败: ' + e.message)
    if (editorRef.value) editorRef.value.style.display = 'none'
  }
}

onMounted(() => {
  // 延迟一点确保 DOM 渲染完毕
  setTimeout(mountEditor, 100)
  loadingTimer = setTimeout(() => {
    if (docEditor === null) {
      ElMessage.error('文档服务器连接超时，请刷新重试')
    }
  }, 15000)
})

// docKey 变了（重新选择了文档），重新挂载
watch(() => props.docKey, () => {
  if (docEditor) {
    try { docEditor.destroyEditor?.() } catch (_) {}
    docEditor = null
  }
  mountEditor()
})

onUnmounted(() => {
  if (loadingTimer) clearTimeout(loadingTimer)
  if (docEditor) {
    try { docEditor.destroyEditor?.() } catch (_) {}
  }
})
</script>

<style scoped>
.document-editor {
  width: 100%;
  height: 100%;
  position: relative;
}
.editor-mount {
  width: 100%;
  height: 100%;
  min-height: 600px;
}
.editor-loading {
  padding: 24px;
}
.loading-hint {
  text-align: center;
  color: #999;
  margin-top: 16px;
  font-size: 14px;
}
</style>
