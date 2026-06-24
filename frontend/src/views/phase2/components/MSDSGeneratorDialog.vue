<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
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
      <div class="section-title-row">
        <div class="section-title">{{ selectedFile.name }}</div>
        <div class="language-toggle">
          <button
            class="lang-btn"
            :class="{ 'lang-btn--active': language === 'cn' }"
            @click="language = 'cn'"
          >中文 MSDS</button>
          <button
            class="lang-btn"
            :class="{ 'lang-btn--active': language === 'en' }"
            @click="language = 'en'"
          >English MSDS</button>
        </div>
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
              <el-input v-model="row.component_cn" size="small" @change="onComponentNameChange(row)" />
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
          <el-table-column label="操作" width="60" fixed="right">
            <template #default="{ row, $index }">
              <el-button
                type="danger"
                size="small"
                link
                :disabled="compositionRows.length <= 1"
                @click="onDeleteCompositionRow($index)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div style="margin-top: 8px">
          <el-button size="small" @click="onAddCompositionRow">+ 添加一行</el-button>
        </div>
        <div class="table-tip">已核对的成分表示在对照表中找到匹配</div>
      </div>

      <!-- 粘贴解析成分 -->
      <div class="form-section">
        <div class="form-section-title">📋 粘贴成分信息（自动解析）</div>
        <div class="paste-row">
          <el-input
            v-model="pastedText"
            type="textarea"
            :rows="2"
            placeholder="粘贴成分信息，如：聚二甲基硅氧烷（硅油）48% 9016-00-6，非离子乳化剂9% 68213-23-0，水43% 7732-18-5"
            style="flex: 1"
          />
          <el-button type="primary" size="small" @click="onParsePasted" :disabled="!pastedText.trim()" style="margin-left: 8px; align-self: flex-end;">
            解析
          </el-button>
        </div>
        <div class="paste-tip">提示：粘贴后自动填入上方成分表格</div>
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
import { ref, watch, computed } from 'vue'
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
const language = ref<'cn' | 'en'>('cn')
const pastedText = ref('')

const dialogTitle = computed(() => language.value === 'en' ? 'Generate MSDS (English)' : '生成 MSDS')

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
    pastedText.value = ''
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
    language.value = 'cn'  // 重置语言
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

/**
 * 解析粘贴的成分信息
 * 规律：名字 + CAS号(X-X-X格式) + 百分比
 * CAS号格式：数字-数字-数字（如 9012-54-8）
 * 解析后自动去后端查表补充缺失的 CAS 号
 */
async function onParsePasted() {
  const text = pastedText.value.trim()
  if (!text) return

  // 预处理：统一分隔符
  let normalized = text
    .replace(/[：:]/g, ' ')
    .replace(/；/g, ' ')
    .replace(/[％%]/g, '%')
    .replace(/\+/g, ' ')
    .replace(/[,，]/g, ' ')
    .replace(/　/g, ' ')
    .replace(/、/g, ' ')

  // 去掉多余空格
  normalized = normalized.replace(/\s+/g, ' ').trim()

  const composition: CompositionItem[] = []
  const seen = new Set<string>()

  // 找所有 CAS号的位置
  const casRegex = /\d{2,7}-\d{1,2}-\d{1,2}/g
  const casMatches: { cas: string; start: number; end: number }[] = []
  let match
  while ((match = casRegex.exec(normalized)) !== null) {
    casMatches.push({
      cas: match[0],
      start: match.index,
      end: match.index + match[0].length,
    })
  }

  // 解析每个有CAS号的成分
  for (let i = 0; i < casMatches.length; i++) {
    const cur = casMatches[i]
    let name = ''
    if (i === 0) {
      name = normalized.slice(0, cur.start).trim()
    } else {
      const prevEnd = casMatches[i - 1].end
      name = normalized.slice(prevEnd, cur.start).trim()
    }

    let nextStart = cur.end
    let nextEnd = i < casMatches.length - 1 ? casMatches[i + 1].start : normalized.length
    let suffix = normalized.slice(nextStart, nextEnd).trim()

    const percentMatch = suffix.match(/^(\d+(?:\.\d+)?)\s*%/)
    let percentage = percentMatch ? percentMatch[1] + '%' : ''

    if (!name || !percentage) continue

    name = name.replace(/\d+$/, '').replace(/\s+/g, ' ').trim()
    if (!name || /^\d+$/.test(name) || /^\d{2,7}-\d{1,2}-\d{1,2}$/.test(name)) continue

    const key = `${name}|${cur.cas}`
    if (!seen.has(key)) {
      seen.add(key)
      composition.push({
        component_cn: name,
        cas: cur.cas,
        percentage: percentage,
        verified: false,
      })
    }
  }

  // 处理没有CAS号的成分（如 "水 70%"）
  if (casMatches.length > 0) {
    const lastCas = casMatches[casMatches.length - 1]
    const lastPart = normalized.slice(lastCas.end).trim()

    const percentMatch = lastPart.match(/^(\d+(?:\.\d+)?)\s*%/)
    if (percentMatch) {
      const percentage = percentMatch[1] + '%'
      const percentIdx = lastPart.indexOf('%')
      let name = lastPart.slice(0, percentIdx).trim()
      name = name.replace(/\d+$/, '').replace(/\s+/g, ' ').trim()

      if (name && !/^\d{2,7}-\d{1,2}-\d{1,2}$/.test(name)) {
        const key = `${name}|`
        if (!seen.has(key)) {
          seen.add(key)
          composition.push({
            component_cn: name,
            cas: '',
            percentage: percentage,
            verified: false,
          })
        }
      }
    }
  }

  if (composition.length === 0) {
    ElMessage.warning('未能解析出成分，请检查格式是否正确')
    return
  }

  // 查表补充缺失的 CAS 号
  const missingCasItems = composition.filter(item => !item.cas)
  if (missingCasItems.length > 0) {
    try {
      const names = missingCasItems.map(item => item.component_cn)
      const res = await msdsGeneratorApi.lookupCas(names)
      const casMap = new Map(res.data.results.map(r => [r.name, r.cas]))

      for (const item of composition) {
        if (!item.cas && casMap.has(item.component_cn)) {
          item.cas = casMap.get(item.component_cn) || ''
        }
      }
    } catch (e) {
      // 查表失败不影响解析结果
    }
  }

  // 只更新成分表格，不修改其他字段
  compositionRows.value = composition
  ElMessage.success(`解析成功：${composition.length} 个成分`)
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

function onAddCompositionRow() {
  compositionRows.value.push({
    component_cn: '',
    cas: '',
    percentage: '',
    verified: false,
  })
}

function onDeleteCompositionRow(index: number) {
  compositionRows.value.splice(index, 1)
}

/**
 * 成分名称变更时，自动查表补充 CAS 号
 */
async function onComponentNameChange(row: CompositionItem) {
  if (!row.component_cn || row.component_cn.trim() === '') {
    return
  }
  if (row.cas) {
    // 已经有 CAS 号了，不需要查
    return
  }

  try {
    const res = await msdsGeneratorApi.lookupCas([row.component_cn])
    if (res.data.results && res.data.results.length > 0) {
      const cas = res.data.results[0].cas
      if (cas) {
        row.cas = cas
        row.verified = true
      }
    }
  } catch (e) {
    // 查表失败不影响使用
  }
}

function onBack() {
  selectedFile.value = null
}

function onClosed() {
  searchKeyword.value = ''
  msdsFiles.value = []
  selectedFile.value = null
  pastedText.value = ''
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
      language: language.value,
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
.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.language-toggle {
  display: flex;
  gap: 4px;
}
.lang-btn {
  height: 28px;
  padding: 0 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-fill-color-light);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.lang-btn:hover { border-color: var(--el-color-primary); }
.lang-btn--active {
  background: var(--el-color-primary);
  color: #fff;
  border-color: var(--el-color-primary);
}

.search-section {
  margin-bottom: 12px;
}

.paste-section {
  margin-bottom: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.paste-section .section-title-row {
  margin-bottom: 8px;
}

.paste-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

.paste-row {
  display: flex;
  align-items: flex-start;
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
