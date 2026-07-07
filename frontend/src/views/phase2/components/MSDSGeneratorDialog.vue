<template>
  <el-dialog
    v-model="visible"
    title="MSDS 产品台账"
    width="900px"
    :append-to-body="true"
    @closed="onClosed"
  >
    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索产品名称..."
        clearable
        @input="onSearch"
        @clear="onSearchClear"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button v-if="newFormulas.length > 0" type="warning" @click="importNewFormulas">
        导入 {{ newFormulas.length }} 个新配方
      </el-button>
      <el-button type="primary" @click="showAddDialog">新增配方</el-button>
    </div>

    <!-- 台账表格 -->
    <el-table
      :data="ledgerList"
      highlight-current-row
      size="small"
      style="width: 100%; margin-bottom: 16px"
      @current-change="onRowClick"
    >
      <el-table-column width="50">
        <template #default="{ row }">
          <el-checkbox :model-value="selectedItem?.id === row.id" @change="onRowClick(row)" />
        </template>
      </el-table-column>
      <el-table-column prop="customs_name" label="报关名称" width="140" />
      <el-table-column label="成分(摘要)" width="180">
        <template #default="{ row }">
          {{ getCompositionSummary(row.composition) }}
        </template>
      </el-table-column>
      <el-table-column prop="appearance" label="外观" width="160" show-overflow-tooltip />
      <el-table-column prop="ion_type" label="离子性" width="80" />
      <el-table-column prop="ph" label="pH值" width="80" />
      <el-table-column prop="version" label="版本" width="60" />
    </el-table>

    <!-- 选中产品详情 -->
    <div v-if="selectedItem" class="detail-section">
      <div class="detail-header">
        <span class="detail-title">选中产品详情</span>
        <el-button size="small" @click="showEditDialog">编辑</el-button>
      </div>
      <div class="detail-content">
        <div class="detail-row">
          <span class="detail-label">报关名称:</span>
          <span>{{ selectedItem.customs_name }}</span>
          <span class="detail-en" v-if="selectedItem.product_name_en"> / {{ selectedItem.product_name_en }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">外观:</span>
          <span>{{ selectedItem.appearance || 'no data' }}</span>
          <span class="detail-en" v-if="selectedItem.appearance_en"> / {{ selectedItem.appearance_en }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">离子性:</span>
          <span>{{ selectedItem.ion_type || 'no data' }}</span>
          <span class="detail-en" v-if="selectedItem.ion_type_en"> / {{ selectedItem.ion_type_en }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">pH值:</span>
          <span>{{ selectedItem.ph || 'no data' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">成分:</span>
          <span>{{ getCompositionDetail(selectedItem.composition) }}</span>
        </div>
      </div>
      <div class="detail-actions">
        <el-button size="small" type="danger" @click="onDelete">删除</el-button>
        <el-button size="small" type="primary" @click="showGenerateDialog('cn')">生成中文MSDS</el-button>
        <el-button size="small" type="primary" @click="showGenerateDialog('en')">生成英文MSDS</el-button>
      </div>
    </div>

    <!-- 新增/编辑配方对话框 -->
    <el-dialog v-model="showForm" :title="editingItem ? '编辑配方' : '新增配方'" width="600px" append-to-body>
      <el-form :model="formData" label-width="100px">
        <el-form-item label="内部编码">
          <el-input v-model="formData.internal_code" placeholder="如 CF463" />
        </el-form-item>
        <el-form-item label="报关名称">
          <el-input v-model="formData.customs_name" placeholder="中文报关名称" />
        </el-form-item>
        <el-form-item label="外观">
          <el-input v-model="formData.appearance" />
        </el-form-item>
        <el-form-item label="离子性">
          <el-input v-model="formData.ion_type" placeholder="阳离子/阴离子/非离子" />
        </el-form-item>
        <el-form-item label="pH值">
          <el-input v-model="formData.ph" placeholder="如 5.0-7.0" />
        </el-form-item>
        <el-form-item label="产品英文名">
          <el-input v-model="formData.product_name_en" />
        </el-form-item>
        <el-form-item label="外观(英文)">
          <el-input v-model="formData.appearance_en" />
        </el-form-item>
        <el-form-item label="离子性(英文)">
          <el-input v-model="formData.ion_type_en" placeholder="Cationic/Anionic/Non-ionic" />
        </el-form-item>
        <el-form-item label="成分">
          <div v-for="(item, idx) in formData.composition" :key="idx" class="composition-row">
            <el-input v-model="item.component_cn" placeholder="成分名" style="width: 120px" />
            <el-input v-model="item.component_en" placeholder="English" style="width: 120px" />
            <el-input v-model="item.cas" placeholder="CAS" style="width: 110px" />
            <el-input v-model="item.percentage" placeholder="%" style="width: 60px" />
            <el-button type="danger" link @click="removeComposition(idx)">删除</el-button>
          </div>
          <el-button size="small" @click="addComposition">+ 添加成分</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" @click="onSaveForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 生成 MSDS 确认对话框 -->
    <el-dialog v-model="showGenerate" title="确认 MSDS 生成信息" width="400px" append-to-body>
      <el-form label-width="80px">
        <el-form-item label="MSDS编号">
          <el-input v-model="generateForm.msds_number" placeholder="如 HHJS-2615" />
        </el-form-item>
        <el-form-item label="修订时间">
          <el-date-picker
            v-model="generateForm.revision_date"
            type="date"
            placeholder="选择日期"
            format="YYYY/MM/DD"
            value-format="YYYY/MM/DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="版次">
          <el-input :value="generateForm.revision" disabled />
        </el-form-item>
        <el-form-item label="更新日期">
          <el-input :value="generateForm.update_date_cn" disabled />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerate = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="onConfirmGenerate">确认生成</el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { msdsLedgerApi, type MsdsLedgerItem, type CompositionItem } from '@/api/msds-ledger'

const props = defineProps<{ modelValue: boolean; orderItems?: any[] }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'generated': [config: any]
}>()

const visible = ref(props.modelValue)
const loading = ref(false)
const orderItemsNames = ref<string[]>([])
const orderItemsWithIngredients = ref<any[]>([])
const newFormulas = ref<any[]>([])
const generating = ref(false)
const searchKeyword = ref('')
const ledgerList = ref<MsdsLedgerItem[]>([])
const selectedItem = ref<MsdsLedgerItem | null>(null)

// 表单相关
const showForm = ref(false)
const editingItem = ref<MsdsLedgerItem | null>(null)
const formData = ref({
  internal_code: '',
  customs_name: '',
  appearance: '',
  ion_type: '',
  ph: '',
  product_name_en: '',
  appearance_en: '',
  ion_type_en: '',
  composition: [] as CompositionItem[],
})

// 生成相关
const showGenerate = ref(false)
const generateLanguage = ref<'cn' | 'en'>('cn')
const generateForm = ref({
  msds_number: '',
  revision_date: '',
  revision: '',
  update_date_cn: '',
})

watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v) {
    searchKeyword.value = ''
    // Extract order items info for filtering and composition check
    if (props.orderItems && props.orderItems.length > 0) {
      const names = [...new Set(props.orderItems.map((it: any) => it.customs_name || it.order?.customs_name || it.pi?.customs_name).filter(Boolean))]
      orderItemsNames.value = names
      orderItemsWithIngredients.value = props.orderItems.map((it: any) => ({
        customs_name: it.customs_name || it.order?.customs_name || '',
        customs_ingredients: it.customs_ingredients || '',
        internal_code: it.internal_code || '',
        appearance: it.appearance || it.order?.appearance || '',
      }))
    } else {
      orderItemsNames.value = []
      orderItemsWithIngredients.value = []
    }
    loadLedger()
  }
})

watch(visible, (v) => emit('update:modelValue', v))

async function loadLedger() {
  loading.value = true
  try {
    const params: any = {}
    if (searchKeyword.value) {
      params.keyword = searchKeyword.value
    }
    const res = await msdsLedgerApi.list(params)
    let items = res.data.items || []
    
    // Filter by order items' customs_names directly
    if (orderItemsNames.value.length > 0) {
      items = items.filter((item: MsdsLedgerItem) => 
        orderItemsNames.value.includes(item.customs_name)
      )
    }
    
    ledgerList.value = items
    
    // Detect new formulas - products with same name but different composition
    newFormulas.value = []
    if (orderItemsWithIngredients.value.length > 0) {
      for (const orderItem of orderItemsWithIngredients.value) {
        if (!orderItem.customs_ingredients) continue
        
        // Normalize ingredients for comparison
        const orderIngredients = orderItem.customs_ingredients.replace(/\s+/g, '').toLowerCase()
        
        // Check if any ledger entry has matching composition
        const hasMatch = items.some((ledgerItem: MsdsLedgerItem) => {
          if (ledgerItem.customs_name !== orderItem.customs_name) return false
          if (!ledgerItem.composition || ledgerItem.composition.length === 0) return false
          
          // Build composition string from ledger
          const ledgerIngredients = ledgerItem.composition
            .map((c: any) => `${c.component_cn}${c.cas}${c.percentage}`)
            .join('+')
            .replace(/\s+/g, '')
            .toLowerCase()
          
          return orderIngredients === ledgerIngredients
        })
        
        if (!hasMatch) {
          // Check if we already added this formula
          const exists = newFormulas.value.some((f: any) => 
            f.customs_name === orderItem.customs_name && f.customs_ingredients === orderItem.customs_ingredients
          )
          if (!exists) {
            newFormulas.value.push(orderItem)
          }
        }
      }
      
      if (newFormulas.value.length > 0) {
        ElMessage.warning(`检测到 ${newFormulas.value.length} 个新配方，请点击"新增配方"添加到台账。`)
      }
    }
  } catch (e: any) {
    ElMessage.error('加载台账失败: ' + (e.message || ''))
  } finally {
    loading.value = false
  }
}

function onSearch() {
  loadLedger()
}

function onSearchClear() {
  searchKeyword.value = ''
  loadLedger()
}

function onRowClick(row: MsdsLedgerItem | null) {
  if (!row) return
  selectedItem.value = selectedItem.value?.id === row.id ? null : row
}

function getCompositionSummary(composition: CompositionItem[] | null) {
  if (!composition || composition.length === 0) return '-'
  return composition.map(c => c.component_cn).join('+')
}

function getCompositionDetail(composition: CompositionItem[] | null) {
  if (!composition || composition.length === 0) return 'no data'
  return composition.map(c => {
    const cas = c.cas ? ` (CAS: ${c.cas})` : ''
    const pct = c.percentage ? ` - ${c.percentage}` : ''
    return `${c.component_cn}${cas}${pct}`
  }).join(', ')
}

function showAddDialog() {
  editingItem.value = null
  formData.value = {
    internal_code: '',
    customs_name: '',
    appearance: '',
    ion_type: '',
    ph: '',
    product_name_en: '',
    appearance_en: '',
    ion_type_en: '',
    composition: [],
  }
  showForm.value = true
}

function showEditDialog() {
  if (!selectedItem.value) return
  editingItem.value = selectedItem.value
  formData.value = {
    internal_code: selectedItem.value.internal_code,
    customs_name: selectedItem.value.customs_name,
    appearance: selectedItem.value.appearance,
    ion_type: selectedItem.value.ion_type,
    ph: selectedItem.value.ph,
    product_name_en: selectedItem.value.product_name_en,
    appearance_en: selectedItem.value.appearance_en,
    ion_type_en: selectedItem.value.ion_type_en,
    composition: selectedItem.value.composition ? [...selectedItem.value.composition] : [],
  }
  showForm.value = true
}

function addComposition() {
  formData.value.composition.push({ component_cn: '', component_en: '', cas: '', percentage: '' })
}

function removeComposition(idx: number) {
  formData.value.composition.splice(idx, 1)
}

async function onSaveForm() {
  try {
    if (editingItem.value) {
      await msdsLedgerApi.update(editingItem.value.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await msdsLedgerApi.create(formData.value)
      ElMessage.success('创建成功')
    }
    showForm.value = false
    loadLedger()
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.message || ''))
  }
}

async function onDelete() {
  if (!selectedItem.value) return
  try {
    await ElMessageBox.confirm('确定删除此配方？', '确认')
    await msdsLedgerApi.delete(selectedItem.value.id)
    ElMessage.success('删除成功')
    selectedItem.value = null
    loadLedger()
  } catch (e) {
    // cancelled
  }
}

function getDefaultDate() {
  const d = new Date()
  d.setMonth(d.getMonth() - 2)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}/${m}/${day}`
}

function showGenerateDialog(lang: 'cn' | 'en') {
  if (!selectedItem.value) return
  generateLanguage.value = lang
  const defaultDate = getDefaultDate()
  const d = new Date(defaultDate)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  
  generateForm.value = {
    msds_number: '',
    revision_date: defaultDate,
    revision: `${y}-${m}`,
    update_date_cn: `${y}年${parseInt(m)}月`,
  }
  showGenerate.value = true
}

async function onConfirmGenerate() {
  if (!selectedItem.value) return
  if (!generateForm.value.msds_number) {
    ElMessage.warning('请输入MSDS编号')
    return
  }
  
  generating.value = true
  try {
    const res = await msdsLedgerApi.generate({
      ledger_id: selectedItem.value.id,
      language: generateLanguage.value,
      msds_number: generateForm.value.msds_number,
      revision_date: generateForm.value.revision_date,
    })
    emit('generated', res.data)
    showGenerate.value = false
    visible.value = false
  } catch (e: any) {
    ElMessage.error('生成失败: ' + (e.message || ''))
  } finally {
    generating.value = false
  }
}

async function importNewFormulas() {
  for (const formula of newFormulas.value) {
    // Parse ingredients string
    const ingredients = formula.customs_ingredients || ''
    const composition = parseIngredients(ingredients)
    
    // Get appearance from orderItems (passed from Phase2Workflow)
    let appearance = ''
    if (formula.internal_code) {
      const orderItem = orderItemsWithIngredients.value.find((item: any) => 
        item.internal_code === formula.internal_code
      )
      if (orderItem && orderItem.appearance) {
        appearance = orderItem.appearance
      }
    }
    // Fallback: try by customs_name from existing ledger
    if (!appearance) {
      const existingItem = ledgerList.value.find((item: MsdsLedgerItem) => 
        item.customs_name === formula.customs_name && item.appearance
      )
      if (existingItem) {
        appearance = existingItem.appearance
      }
    }
    
    try {
      await msdsLedgerApi.create({
        internal_code: formula.internal_code || '',
        customs_name: formula.customs_name,
        appearance: appearance,
        ion_type: '',
        ph: '',
        composition: composition,
        product_name_en: '',
        appearance_en: '',
        ion_type_en: '',
      })
    } catch (e) {
      console.error('Failed to import formula:', e)
    }
  }
  ElMessage.success(`已导入 ${newFormulas.value.length} 个新配方`)
  newFormulas.value = []
  loadLedger()
}

function parseIngredients(ingredients: string): any[] {
  if (!ingredients) return []
  
  const result = []
  
  // Format 1: "成分名：CAS号，含量%" (space separated)
  // Format 2: "成分名CAS号：含量%" (+ separated)
  // First try space-separated format (more common)
  const spaceParts = ingredients.split(/\s+/).filter(p => p.trim())
  
  // Check if it's space-separated with colons
  if (ingredients.includes('：') && spaceParts.length > 1) {
    // Space-separated format: "十二烷基苯磺酸钠：25155-30-0，40%"
    for (const part of spaceParts) {
      const trimmed = part.trim()
      if (!trimmed) continue
      
      // Extract CAS number
      const casMatch = trimmed.match(/(\d{2,7}-\d{1,2}-\d{1,2})/)
      const cas = casMatch ? casMatch[1] : ''
      
      // Extract percentage (Chinese comma or regular comma)
      const pctMatch = trimmed.match(/[，,]\s*(\d+(?:\.\d+)?)\s*[％%]/)
      const percentage = pctMatch ? pctMatch[1] + '%' : ''
      
      // Extract component name (before colon)
      let componentName = trimmed
      const colonIdx = trimmed.indexOf('：')
      if (colonIdx > 0) {
        componentName = trimmed.substring(0, colonIdx).trim()
      }
      
      if (componentName) {
        result.push({
          component_cn: componentName,
          component_en: '',
          cas: cas,
          percentage: percentage,
        })
      }
    }
  } else {
    // Plus-separated format: "成分名CAS号：含量%+成分名CAS号：含量%"
    const parts = ingredients.split('+')
    for (const part of parts) {
      const trimmed = part.trim()
      if (!trimmed) continue
      
      const casMatch = trimmed.match(/(\d{2,7}-\d{1,2}-\d{1,2})/)
      const cas = casMatch ? casMatch[1] : ''
      
      const pctMatch = trimmed.match(/(\d+(?:\.\d+)?)\s*[％%]/)
      const percentage = pctMatch ? pctMatch[1] + '%' : ''
      
      let componentName = trimmed
      if (casMatch) {
        componentName = trimmed.substring(0, casMatch.index!).trim()
      } else if (pctMatch) {
        componentName = trimmed.substring(0, pctMatch.index!).trim()
      }
      componentName = componentName.replace(/[：:]\s*$/, '').trim()
      
      if (componentName) {
        result.push({
          component_cn: componentName,
          component_en: '',
          cas: cas,
          percentage: percentage,
        })
      }
    }
  }
  
  return result
}

function onClosed() {
  searchKeyword.value = ''
  ledgerList.value = []
  selectedItem.value = null
  orderItemsNames.value = []
}
</script>

<style scoped>
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.detail-section {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
  background: var(--el-fill-color-lighter);
}
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.detail-title {
  font-weight: 600;
}
.detail-content {
  font-size: 13px;
  line-height: 1.8;
}
.detail-row {
  display: flex;
  gap: 8px;
}
.detail-label {
  font-weight: 500;
  min-width: 70px;
  color: var(--el-text-color-secondary);
}
.detail-en {
  color: var(--el-text-color-placeholder);
}
.detail-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
.composition-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
</style>
