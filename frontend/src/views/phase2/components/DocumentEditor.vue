<template>
  <div class="document-editor">
    <!-- OnlyOffice 编辑器挂载点 -->
    <div ref="editorRef" id="onlyoffice-editor" class="editor-mount">
      <!-- 骨架屏放在挂载点内部，清空 innerHTML 时会一起清除 -->
      <div class="editor-loading">
        <el-skeleton :rows="10" animated />
        <div class="loading-hint">正在连接文档服务器...</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  documentServerUrl: string
  docKey: string
  token: string
  downloadUrl: string
  url?: string       // OnlyOffice 可访问的 URL
  callbackUrl?: string  // 后端回调地址（OnlyOffice 保存时回调）
  docType?: string  // "cell" | "word" | "slide"
  title?: string    // 文档标题，传给 OnlyOffice 显示
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
  return {
    width: "100%",
    height: "100%",
    document: {
      fileType: ext,
      key: props.docKey,
      title: props.title || `Document.${ext}`,
      url: docUrl,
    },
    documentType: dt,
    token: props.token,
    editorConfig: {
      callbackUrl: props.callbackUrl || `http://host.docker.internal:8000/api/v1/onlyoffice/callback?doc_key=${props.docKey}`,
      mode: 'edit',
      forcesave: true,
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
    // 直接使用传入的 documentServerUrl
    script.src = `${props.documentServerUrl}/web-apps/apps/api/documents/api.js`
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('OnlyOffice API 加载失败'))
    document.head.appendChild(script)
  })
}

async function mountEditor() {
  // Try Vue ref first, fall back to direct DOM query
  let el = editorRef.value
  if (!el) {
    el = document.getElementById('onlyoffice-editor')
  }
  if (!el) {
    ElMessage.error('编辑器容器未找到')
    return
  }
  try {
    // 显示挂载点（骨架屏在内部）
    el.style.display = 'block'

    await loadOnlyOfficeAPI()
    const DocsAPI = (window as any).DocsAPI
    if (!DocsAPI) throw new Error('DocsAPI 未定义')

    // 清空骨架屏（骨架屏现在在 el 内部，innerHTML 会清除）
    el.innerHTML = ''

    const config = buildConfig()
    docEditor = new DocsAPI.DocEditor(el.id, config)
  } catch (e: any) {
    ElMessage.error('文档服务器连接失败，请检查服务状态')
    if (editorRef.value) editorRef.value.style.display = 'none'
  }
}

onMounted(() => {
  nextTick(() => {
    setTimeout(mountEditor, 100)
    loadingTimer = setTimeout(() => {
      if (docEditor === null) {
        ElMessage.error('文档服务器连接超时，请刷新重试')
      }
    }, 20000)
  })
})

// docKey 变了（重新选择了文档），重新挂载
watch(() => props.docKey, () => {
  if (loadingTimer) {
    clearTimeout(loadingTimer)
    loadingTimer = null
  }
  if (docEditor) {
    try { docEditor.destroyEditor?.() } catch (_) {}
    docEditor = null
  }
  nextTick(() => mountEditor())
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
  display: flex;
  flex-direction: column;
}
.editor-mount {
  width: 100%;
  height: 100%;
  min-height: 0;
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
