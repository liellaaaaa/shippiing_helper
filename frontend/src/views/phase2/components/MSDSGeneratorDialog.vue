<template>
  <el-dialog
    v-model="visible"
    title="生成 MSDS"
    width="700px"
    :append-to-body="true"
    class="msds-generator-dialog"
    @closed="onClosed"
  >
    <!-- 搜索区域 -->
    <div class="search-section">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索产品名称..."
        clearable
        @input="onSearchInput"
        @clear="onSearchClear"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <!-- 旧 MSDS 文件列表 -->
    <div v-if="!selectedFile && msdsFiles.length > 0" class="file-list">
      <div class="section-title">选择旧 MSDS 文件</div>
      <div
        v-for="file in msdsFiles"
        :key="file.path"
        class="file-item"
        @click="onSelectFile(file)"
      >
        <el-icon><Document /></el-icon>
        <span>{{ file.name }}</span>
      </div>
    </div>

    <div v-else-if="!selectedFile && searchKeyword && !loading" class="no-results">
      <el-empty description="未找到匹配的 MSDS 文件" />
    </div>

    <!-- 编辑区域 -->
    <div v-if="selectedFile" class="edit-section">
      <div class="section-title">
        {{ selectedFile.name }}
      </div>

      <!-- 产品信息 -->
      <div class="form-section">
        <div class="form-section-title">产品信息</div>
        <el-form label-width="100px" label-position="left">
          <el-form-item label="MSDS编号">
            <el-input v-model="formData.msds_number" placeholder="如 HHJS-2615" />
          </el-form-item>
          <el-form-item label="修订时间">
            <el-date-picker
              v-model="formData.revision_date"
              type="date"
              placeholder="选择日期"
              format="YYYY/MM/DD"
              value-format="YYYY/MM/DD"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="产品名称">
            <el-input v-model="formData.productName" placeholder="产品名称" />
          </el-form-item>
          <el-form-item label="外观">
            <el-input v-model="formData.appearance" placeholder="外观描述" />
          </el-form-item>
          <el-form-item label="外观(英文)">
            <el-input v-model="formData.appearanceEn" disabled />
          </el-form-item>
        </el-form>
      </div>

      <!-- 成分表格 -->
      <div class="form-section">
        <div class="form-section-title">成分</div>
        <el-table :data="compositionRows" border size="small" class="composition-table">
          <el-table-column label="成分(中文)" prop="component_cn">
            <template #default="{ row }">
              <el-input v-model="row.component_cn" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="CAS NO." prop="cas" width="140">
            <template #default="{ row }">
              <el-input v-model="row.cas" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="含量" prop="percentage" width="100">
            <template #default="{ row }">
              <el-input v-model="row.percentage" size="small" />
            </template>
          </el-table-column>
          <el-table-column label="已核对" prop="verified" width="70">
            <template #default="{ row }">
              <el-tag v-if="row.verified" type="success" size="small">是</el-tag>
              <el-tag v-else type="warning" size="small">否</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div class="table-tip">已核对的成分表示在对照表中找到匹配</div>
      </div>

      <!-- 理化特性 -->
      <div class="form-section">
        <div class="form-section-title">理化特性</div>
        <el-form label-width="130px" label-position="left">
          <el-form-item label="外观与性状">
            <el-input v-model="formData.physicochemical.appearance" />
          </el-form-item>
          <el-form-item label="离子性">
            <el-input v-model="formData.physicochemical.ion_type" />
          </el-form-item>
          <el-form-item label="PH值">
            <el-input v-model="formData.physicochemical.ph" />
          </el-form-item>
          <el-form-item label="熔点">
            <el-input v-model="formData.physicochemical.melting_point" />
          </el-form-item>
          <el-form-item label="沸点/沸点范围">
            <el-input v-model="formData.physicochemical.boiling_point" />
          </el-form-item>
          <el-form-item label="相对密度">
            <el-input v-model="formData.physicochemical.density" />
          </el-form-item>
          <el-form-item label="闪点">
            <el-input v-model="formData.physicochemical.flash_point" />
          </el-form-item>
          <el-form-item label="溶解性">
            <el-input v-model="formData.physicochemical.solubility" />
          </el-form-item>
        </el-form>
      </div>

      <!-- 翻译按钮预留 -->
      <div class="form-section">
        <el-button type="info" disabled>翻译为英文（后续实现）</el-button>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button v-if="selectedFile" @click="onBack">重新选择</el-button>
      <el-button
        v-if="selectedFile"
        type="primary"
        :loading="loading"
        @click="onGenerate"
      >
        生成 MSDS
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Document } from '@element-plus/icons-vue'
import { msdsGeneratorApi, type MSDSFile, type CompositionItem } from '@/api/msds_generator'

interface Physicochemical {
  appearance: string
  ion_type: string
  ph: string
  melting_point: string
  boiling_point: string
  density: string
  flash_point: string
  solubility: string
}

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'generated': [config: any]  // emit OnlyOffice config to parent
}>()

const visible = ref(props.modelValue)
const loading = ref(false)
const searchKeyword = ref('')
const msdsFiles = ref<MSDSFile[]>([])
const selectedFile = ref<MSDSFile | null>(null)

const formData = ref({
  msds_number: '',
  revision_date: '',
  productName: '',
  appearance: '',
  appearanceEn: '',
  physicochemical: {
    appearance: '',
    ion_type: '',
    ph: '',
    melting_point: '',
    boiling_point: '',
    density: '',
    flash_point: '',
    solubility: '',
  } as Physicochemical,
})

const compositionRows = ref<CompositionItem[]>([])

let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v) {
    // Reset state
    searchKeyword.value = ''
    msdsFiles.value = []
    selectedFile.value = null
    compositionRows.value = []
    formData.value = {
      msds_number: '',
      revision_date: '',
      productName: '',
      appearance: '',
      appearanceEn: '',
      physicochemical: {
        appearance: '',
        ion_type: '',
        ph: '',
        melting_point: '',
        boiling_point: '',
        density: '',
        flash_point: '',
        solubility: '',
      },
    }
  }
})

watch(visible, (v) => emit('update:modelValue', v))

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  if (!searchKeyword.value.trim()) {
    msdsFiles.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    loading.value = true
    try {
      const res = await msdsGeneratorApi.searchMSDS(searchKeyword.value)
      msdsFiles.value = res.data.files || []
    } catch (e: any) {
      ElMessage.error('搜索失败: ' + (e.message || ''))
    } finally {
      loading.value = false
    }
  }, 300)
}

function onSearchClear() {
  msdsFiles.value = []
  selectedFile.value = null
}

async function onSelectFile(file: MSDSFile) {
  selectedFile.value = file
  loading.value = true

  try {
    // 直接从旧 MSDS 文件解析产品信息、成分、理化特性
    const res = await msdsGeneratorApi.parseMSDS(file.path)
    if (res.data.error) {
      ElMessage.error('解析 MSDS 文件失败: ' + res.data.error)
      return
    }

    const data = res.data
    formData.value.msds_number = data.msds_number || ''
    formData.value.revision_date = data.revision_date || ''
    formData.value.productName = data.product_name || ''
    compositionRows.value = data.composition || []

    // 填充理化特性（映射 backend 字段到前端表单）
    const pc = data.physicochemical || {}
    formData.value.physicochemical = {
      appearance: pc.physical_form || '',
      ion_type: pc.ion_type || '',
      ph: pc.ph || '',
      melting_point: pc.melting_point || '',
      boiling_point: pc.boiling_point || '',
      density: pc.density || '',
      flash_point: pc.flash_point || '',
      solubility: pc.solubility || '',
    }
  } catch (e: any) {
    ElMessage.error('解析 MSDS 文件失败: ' + (e.message || ''))
  } finally {
    loading.value = false
  }
}

function onBack() {
  selectedFile.value = null
}

function onClosed() {
  searchKeyword.value = ''
  msdsFiles.value = []
  selectedFile.value = null
}

async function onGenerate() {
  if (!selectedFile.value) return

  loading.value = true
  try {
    const request = {
      msds_file_path: selectedFile.value.path,
      product_name: formData.value.productName,
      composition: compositionRows.value,
      physicochemical: formData.value.physicochemical,
      msds_number: formData.value.msds_number,
      revision_date: formData.value.revision_date,
    }
    const res = await msdsGeneratorApi.generate(request)
    emit('generated', res.data)
    visible.value = false
  } catch (e: any) {
    ElMessage.error('生成 MSDS 失败: ' + (e.message || ''))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.search-section {
  margin-bottom: 16px;
}

.file-list {
  max-height: 300px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px;
}

.file-item:hover {
  background-color: #f5f7fa;
}

.no-results {
  padding: 20px 0;
}

.section-title {
  font-weight: 600;
  margin-bottom: 12px;
  color: #303133;
}

.edit-section {
  max-height: 500px;
  overflow-y: auto;
}

.form-section {
  margin-bottom: 20px;
}

.form-section-title {
  font-weight: 600;
  margin-bottom: 12px;
  color: #606266;
  border-left: 3px solid #409eff;
  padding-left: 8px;
}

.composition-table {
  margin-bottom: 8px;
}

.table-tip {
  font-size: 12px;
  color: #909399;
}
</style>
