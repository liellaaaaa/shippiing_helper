<template>
  <div class="pi-upload-dragger">
    <el-upload
      class="dragger"
      drag
      :auto-upload="false"
      :show-file-list="false"
      :on-change="handleFileChange"
      :accept="acceptTypes"
    >
      <el-icon class="el-icon--upload"><upload-filled /></el-icon>
      <div class="el-upload__text">
        拖拽 PI 文件到此处，或 <em>点击上传</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">支持 .xls / .xlsx / .pdf 文件，大小不超过 10MB</div>
      </template>
    </el-upload>
  </div>
</template>

<script setup lang="ts">
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const emit = defineEmits<{
  fileSelected: [file: File]
}>()

const acceptTypes = '.xls,.xlsx,.pdf'

const handleFileChange = (uploadFile: { raw?: File }) => {
  const file = uploadFile.raw
  if (!file) return

  // Validate file size (10MB)
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件大小超过 10MB 限制')
    return
  }

  // Validate file extension
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (ext !== 'xls' && ext !== 'xlsx' && ext !== 'pdf') {
    ElMessage.error('不支持的文件格式，请上传 .xls、.xlsx 或 .pdf 文件')
    return
  }

  emit('fileSelected', file)
}
</script>

<style scoped>
.pi-upload-dragger { width: 100%; }
.dragger :deep(.el-upload) { width: 100%; }
.dragger :deep(.el-upload-dragger) {
  padding: 32px 20px;
  border-radius: 12px;
  border: 2px dashed var(--el-border-color, #dcdfe6);
  transition: border-color 0.2s;
}
.dragger :deep(.el-upload-dragger:hover) {
  border-color: var(--color-primary, #0077cc);
}
</style>