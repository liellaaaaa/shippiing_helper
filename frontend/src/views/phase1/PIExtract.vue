<template>
  <div class="pi-extract-page">
    <div class="page-header">
      <h1 class="page-title">PI 文件提取</h1>
      <p class="page-subtitle">上传 PI 合同文件，自动解析并关联产品知识库</p>
    </div>

    <div class="page-content">
      <div class="content-left">
        <el-card class="upload-card">
          <template #header>
            <div class="card-header">
              <span>上传 PI 文件</span>
            </div>
          </template>
          <div class="upload-placeholder">
            <el-icon :size="48"><upload-filled /></el-icon>
            <p>拖拽或点击上传 PI 文件</p>
            <p class="upload-hint">支持 .xls / .xlsx 文件</p>
          </div>
        </el-card>

        <el-card class="history-card" style="margin-top: 16px;">
          <template #header>
            <div class="card-header">
              <span>历史查询</span>
            </div>
          </template>
          <el-input v-model="searchPiNo" placeholder="搜索 PI 号" />
          <el-button type="primary" style="margin-top: 12px; width: 100%;" @click="queryContracts">
            查询
          </el-button>
        </el-card>
      </div>

      <div class="content-right">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>解析预览</span>
              <el-tag v-if="parsedData" type="success">已解析</el-tag>
            </div>
          </template>
          <div v-if="!parsedData" class="preview-placeholder">
            <p>上传文件后将显示解析结果</p>
          </div>
          <div v-else>
            <!-- PiPreviewTable will go here in FE-4 -->
            <p>解析完成，等待预览组件...</p>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const searchPiNo = ref('')
const parsedData = ref(null)

const queryContracts = () => {
  ElMessage.info('查询功能待实现')
}
</script>

<style scoped>
.pi-extract-page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 28px; font-weight: 600; color: var(--color-text-primary, #303133); margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: var(--color-text-secondary, #909399); margin: 0; }

.page-content { display: grid; grid-template-columns: 400px 1fr; gap: 20px; }
.content-left { display: flex; flex-direction: column; }
.content-right { min-height: 400px; }

.upload-card, .history-card { border-radius: 12px; }
.card-header { font-weight: 600; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }

.upload-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 20px; color: var(--color-text-secondary, #909399); }
.upload-placeholder .el-icon { color: var(--color-primary, #0077cc); margin-bottom: 16px; }
.upload-placeholder p { margin: 4px 0; }
.upload-hint { font-size: 12px; color: var(--color-text-placeholder, #c0c4cc); }

.preview-placeholder { display: flex; align-items: center; justify-content: center; height: 200px; color: var(--color-text-placeholder, #c0c4cc); }
</style>