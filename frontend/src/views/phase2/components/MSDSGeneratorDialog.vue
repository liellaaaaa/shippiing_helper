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
      <el-button v-if="newFormulas.length > 0" type="warning" @click="toggleEditList">
        {{ showEditList ? '收起' : '导入' }} {{ newFormulas.length }} 个新配方
      </el-button>
      <el-button type="primary" @click="showAddDialog">新增配方</el-button>
      <el-button
        :type="batchMode ? 'success' : 'default'"
        @click="toggleBatchMode"
      >
        {{ batchMode ? '退出批量' : '批量选择' }}
      </el-button>
    </div>

    <!-- 新配方可编辑列表 -->
    <div v-if="showEditList && newFormulas.length > 0" class="edit-list-section">
      <div class="edit-list-header">
        <span class="edit-list-title">新配方（可编辑后导入）</span>
        <div class="edit-list-header-right">
          <span v-if="mismatchCount > 0" class="mismatch-hint">{{ mismatchCount }} 个配方含量与台账不一致，导入前请核对</span>
          <el-button size="small" type="success" @click="importAllFormulas">确认导入</el-button>
        </div>
      </div>
      <div class="edit-list-content">
        <div
          v-for="(formula, idx) in newFormulas"
          :key="idx"
          class="formula-edit-card"
          :class="{ 'has-error': importErrors[idx] }"
        >
          <div class="formula-edit-row">
            <div class="formula-field">
              <label>报关名称 <span class="req">*</span></label>
              <el-input
                v-model="formula.customs_name"
                size="small"
                :class="{ 'input-error': importErrors[idx]?.includes('报关名称') }"
              />
            </div>
            <div class="formula-field">
              <label>外观 <span class="req">*</span></label>
              <el-input
                v-model="formula.appearance"
                size="small"
                :class="{ 'input-error': importErrors[idx]?.includes('外观') }"
              />
            </div>
            <div class="formula-field">
              <label>离子性 <span class="req">*</span></label>
              <el-select
                v-model="formula.ion_type"
                size="small"
                placeholder="请选择"
                :class="{ 'input-error': importErrors[idx]?.includes('离子性') }"
              >
                <el-option label="阳离子" value="阳离子" />
                <el-option label="阴离子" value="阴离子" />
                <el-option label="非离子" value="非离子" />
              </el-select>
            </div>
            <div class="formula-field">
              <label>pH值 <span class="req">*</span></label>
              <el-input
                v-model="formula.ph"
                size="small"
                placeholder="5.0-7.0"
                :class="{ 'input-error': importErrors[idx]?.includes('pH值') }"
              />
            </div>
          </div>
          <div class="formula-edit-row">
            <div class="formula-field formula-field-wide">
              <label>成分表</label>
              <table class="composition-table">
                <thead>
                  <tr>
                    <th style="width:40%">组分</th>
                    <th style="width:35%">CAS NO.</th>
                    <th style="width:15%">含量</th>
                    <th style="width:10%">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(comp, ci) in formula.composition" :key="ci">
                    <td>
                      <el-input
                        v-model="comp.component_cn"
                        size="small"
                        placeholder="必填"
                        :class="{ 'input-error': importErrors[idx]?.includes('成分「组分」') }"
                      />
                    </td>
                    <td><el-input v-model="comp.cas" size="small" placeholder="如 123-45-6" /></td>
                    <td><el-input v-model="comp.percentage" size="small" placeholder="如 30%" /></td>
                    <td><el-button size="small" type="danger" link @click="removeFormulaComp(formula, ci)">删除</el-button></td>
                  </tr>
                </tbody>
              </table>
              <el-button size="small" @click="addFormulaComp(formula)">+ 添加成分</el-button>
              <div v-if="formula.composition.length === 0" class="form-error">至少添加一行成分</div>
            </div>
          </div>
          <div class="formula-actions">
            <el-tag v-if="formula.pctMismatch" type="warning" size="small">含量与台账不一致</el-tag>
            <el-button size="small" type="danger" link @click="removeNewFormula(idx)">移除</el-button>
          </div>
          <div v-if="importErrors[idx]" class="form-error">缺少必填项：{{ importErrors[idx].join('、') }}</div>
        </div>
      </div>
    </div>

    <!-- 台账表格 -->
    <el-table
      ref="tableRef"
      :data="ledgerList"
      :highlight-current-row="!batchMode"
      size="small"
      style="width: 100%; margin-bottom: 16px"
      @current-change="onRowClick"
      @selection-change="onSelectionChange"
    >
      <el-table-column v-if="batchMode" type="selection" width="50" />
      <el-table-column v-else width="50">
        <template #default="{ row }">
          <el-checkbox :model-value="selectedItem?.id === row.id" @change="onRowClick(row)" />
        </template>
      </el-table-column>
      <el-table-column prop="customs_name" label="报关名称" width="140" />
      <el-table-column label="成分" min-width="200">
        <template #default="{ row }">
          {{ getCompositionFull(row.composition) }}
        </template>
      </el-table-column>
      <el-table-column prop="appearance" label="外观" width="160" show-overflow-tooltip />
      <el-table-column prop="ion_type" label="离子性" width="80" />
      <el-table-column prop="ph" label="pH值" width="80" />
    </el-table>

    <!-- 单选操作按钮 -->
    <div v-if="!batchMode && selectedItem" class="detail-actions">
      <el-button size="small" @click="showEditDialog">编辑</el-button>
      <el-button size="small" type="danger" @click="onDelete">删除</el-button>
      <el-button size="small" type="primary" @click="showGenerateDialog('cn')">生成中文MSDS</el-button>
      <el-button size="small" type="primary" @click="showGenerateDialog('en')">生成英文MSDS</el-button>
    </div>

    <!-- 批量操作按钮 -->
    <div v-if="batchMode && selectedItems.length > 0" class="detail-actions">
      <el-button type="primary" @click="showBatchGenerateDialog">
        批量生成MSDS ({{ selectedItems.length }}个产品)
      </el-button>
    </div>

    <!-- 新增/编辑配方对话框 -->
    <el-dialog v-model="showForm" :title="editingItem ? '编辑配方' : '新增配方'" width="700px" append-to-body>
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-form-item label="报关名称" prop="customs_name">
          <el-input v-model="formData.customs_name" placeholder="中文报关名称" />
        </el-form-item>
        <el-form-item label="外观" prop="appearance">
          <el-input v-model="formData.appearance" />
        </el-form-item>
        <el-form-item label="离子性" prop="ion_type">
          <el-select v-model="formData.ion_type" placeholder="请选择">
            <el-option label="阳离子" value="阳离子" />
            <el-option label="阴离子" value="阴离子" />
            <el-option label="非离子" value="非离子" />
          </el-select>
        </el-form-item>
        <el-form-item label="pH值" prop="ph">
          <el-input v-model="formData.ph" placeholder="如 5.0-7.0" />
        </el-form-item>
        <el-form-item label="成分表" prop="composition">
          <table class="composition-table">
            <thead>
              <tr>
                <th style="width:40%">组分</th>
                <th style="width:35%">CAS NO.</th>
                <th style="width:15%">含量</th>
                <th style="width:10%">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in formData.composition" :key="idx">
                <td><el-input v-model="item.component_cn" placeholder="必填" size="small" /></td>
                <td><el-input v-model="item.cas" placeholder="如 123-45-6" size="small" /></td>
                <td><el-input v-model="item.percentage" placeholder="如 30%" size="small" /></td>
                <td><el-button type="danger" link @click="removeComposition(idx)">删除</el-button></td>
              </tr>
            </tbody>
          </table>
          <el-button size="small" @click="addComposition()">+ 添加成分</el-button>
          <div v-if="formData.composition.length === 0" class="form-error">至少添加一行成分</div>
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

    <!-- 批量生成对话框 -->
    <BatchGenerateDialog
      v-model="showBatchGenerate"
      :selected-items="selectedItems"
      @generated="onBatchGenerated"
    />
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { msdsLedgerApi, type MsdsLedgerItem, type CompositionItem } from '@/api/msds-ledger'
import BatchGenerateDialog from './BatchGenerateDialog.vue'

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
const tableRef = ref<any>(null)
const selectedItem = ref<MsdsLedgerItem | null>(null)
const showEditList = ref(false)
const importErrors = ref<Record<number, string[]>>({})
const mismatchCount = computed(() => newFormulas.value.filter((f: any) => f.pctMismatch).length)

// 批量选择相关
const batchMode = ref(false)
const selectedItems = ref<MsdsLedgerItem[]>([])
const showBatchGenerate = ref(false)

// 表单相关
const showForm = ref(false)
const editingItem = ref<MsdsLedgerItem | null>(null)
const formData = ref({
  customs_name: '',
  appearance: '',
  ion_type: '',
  ph: '',
  product_name_en: '',
  appearance_en: '',
  ion_type_en: '',
  composition: [] as CompositionItem[],
})

const formRef = ref<FormInstance>()

const formRules: FormRules = {
  customs_name: [{ required: true, message: '请输入报关名称', trigger: 'blur' }],
  appearance: [{ required: true, message: '请输入外观', trigger: 'blur' }],
  ion_type: [{ required: true, message: '请选择离子性', trigger: 'change' }],
  ph: [{ required: true, message: '请输入pH值', trigger: 'blur' }],
  composition: [{
    validator: (_rule: any, value: any[], callback: any) => {
      if (!value || value.length === 0) {
        callback(new Error('至少添加一行成分'))
      } else if (value.some((v: any) => !v.component_cn?.trim())) {
        callback(new Error('每行成分的「组分」为必填'))
      } else {
        callback()
      }
    },
    trigger: 'change',
  }],
}

// 生成相关
const showGenerate = ref(false)
const generateLanguage = ref<'cn' | 'en'>('cn')
const generateForm = ref({
  msds_number: '',
  revision_date: '',
  revision: '',
  update_date_cn: '',
})

function generateRandomPh(): string {
  const x = Math.floor(Math.random() * 2) + 5 // 5 or 6
  return `${x}±1`
}

// 归一化 CAS：去掉前导零（"0026545-58-4" -> "26545-58-4"）
function normCas(s: string): string {
  return (s || '').replace(/(\b0+)(\d)/g, '$2')
}

// 归一化含量：提取数值（"30%"、"30.0%"、"30 %" -> "30"），无法解析返回空串
function normPct(s: string): string {
  const m = String(s ?? '').match(/(\d+(?:\.\d+)?)/)
  return m ? String(parseFloat(m[1])) : ''
}

// 成分匹配级别：full = CAS 与含量全部一致；pct = CAS 一致但含量不同；none = CAS 不一致或无法比较
function compositionMatchLevel(orderList: any[], ledgerList: any[]): 'full' | 'pct' | 'none' {
  const orderMap: Record<string, string> = {}
  for (const c of orderList || []) {
    const cas = normCas(c.cas || '').trim()
    if (cas) orderMap[cas] = normPct(c.percentage)
  }
  const ledgerMap: Record<string, string> = {}
  for (const c of ledgerList || []) {
    const cas = normCas(c.cas || '').trim()
    if (cas) ledgerMap[cas] = normPct(c.percentage)
  }
  const oKeys = Object.keys(orderMap).sort()
  const lKeys = Object.keys(ledgerMap).sort()
  if (oKeys.length === 0 || oKeys.join(',') !== lKeys.join(',')) return 'none'
  for (const cas of oKeys) {
    const op = orderMap[cas]
    const lp = ledgerMap[cas]
    if (op && lp && op !== lp) return 'pct'
  }
  return 'full'
}

// 校验新配方必填项，返回是否全部通过；失败时填充 importErrors 供界面标红
function validateNewFormulas(): boolean {
  const errs: Record<number, string[]> = {}
  newFormulas.value.forEach((f: any, idx: number) => {
    const missing: string[] = []
    if (!f.customs_name?.trim()) missing.push('报关名称')
    if (!f.appearance?.trim()) missing.push('外观')
    if (!f.ion_type?.trim()) missing.push('离子性')
    if (!f.ph?.trim()) missing.push('pH值')
    if (!f.composition || f.composition.length === 0) missing.push('成分表')
    else if (f.composition.some((c: any) => !c.component_cn?.trim())) missing.push('成分「组分」')
    if (missing.length) errs[idx] = missing
  })
  importErrors.value = errs
  return Object.keys(errs).length === 0
}

watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v) {
    searchKeyword.value = ''
    showEditList.value = false
    // Extract order items info for filtering and composition check
    if (props.orderItems && props.orderItems.length > 0) {
      const names = [...new Set(props.orderItems.map((it: any) => it.customs_name || it.order?.customs_name || it.pi?.customs_name).filter(Boolean))]
      orderItemsNames.value = names
      orderItemsWithIngredients.value = props.orderItems.map((it: any) => ({
        customs_name: it.customs_name || it.order?.customs_name || '',
        customs_ingredients: it.customs_ingredients || '',
        appearance: it.appearance || it.order?.appearance || '',
      }))
    } else {
      orderItemsNames.value = []
      orderItemsWithIngredients.value = []
    }
    loadLedger().then(() => {
      autoSelectMatchingItems()
      if (mismatchCount.value > 0) {
        ElMessage.warning(`${mismatchCount.value} 个配方含量与台账不一致，已作为新配方列出，导入前请核对`)
      }
    })
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
    importErrors.value = {}
    if (orderItemsWithIngredients.value.length > 0) {
      for (const orderItem of orderItemsWithIngredients.value) {
        if (!orderItem.customs_ingredients) continue

        const parsedComp = parseIngredients(orderItem.customs_ingredients)
        // 与台账同名单据项比对：full = 已在库；pct = CAS 一致但含量不同（按新配方列出并标记）；none = 库里没有
        let matchLevel: 'full' | 'pct' | 'none' = 'none'
        for (const ledgerItem of items) {
          if (ledgerItem.customs_name !== orderItem.customs_name) continue
          if (!ledgerItem.composition || ledgerItem.composition.length === 0) continue
          const level = compositionMatchLevel(parsedComp, ledgerItem.composition)
          if (level === 'full') {
            matchLevel = 'full'
            break
          }
          if (level === 'pct' && matchLevel === 'none') matchLevel = 'pct'
        }

        if (matchLevel === 'full') continue

        // Check if we already added this formula
        const exists = newFormulas.value.some((f: any) => 
          f.customs_name === orderItem.customs_name && f.customs_ingredients === orderItem.customs_ingredients
        )
        if (!exists) {
          newFormulas.value.push({
            ...orderItem,
            ion_type: '',
            ph: generateRandomPh(),
            composition: parsedComp,
            pctMismatch: matchLevel === 'pct',
          })
        }
      }
      
      if (newFormulas.value.length > 0) {
        showEditList.value = true
      }
    }
  } catch (e: any) {
    ElMessage.error('加载台账失败: ' + (e.message || ''))
  } finally {
    loading.value = false
  }
}

function toggleEditList() {
  showEditList.value = !showEditList.value
}

function removeNewFormula(idx: number) {
  newFormulas.value.splice(idx, 1)
  delete importErrors.value[idx]
  if (newFormulas.value.length === 0) {
    showEditList.value = false
  }
}

function addFormulaComp(formula: any) {
  if (!formula.composition) {
    formula.composition = []
  }
  formula.composition.push({ component_cn: '', component_en: '', cas: '', percentage: '' })
}

function removeFormulaComp(formula: any, idx: number) {
  formula.composition.splice(idx, 1)
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

function getCompositionFull(composition: CompositionItem[] | null) {
  if (!composition || composition.length === 0) return '-'
  return composition.map(c => {
    const pct = c.percentage ? ` ${c.percentage}` : ''
    const cas = c.cas ? ` (${c.cas})` : ''
    return `${c.component_cn}${cas}${pct}`
  }).join(' + ')
}

function showAddDialog() {
  editingItem.value = null
  formData.value = {
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
    customs_name: selectedItem.value.customs_name,
    appearance: selectedItem.value.appearance,
    ion_type: selectedItem.value.ion_type,
    ph: selectedItem.value.ph,
    product_name_en: selectedItem.value.product_name_en || '',
    appearance_en: selectedItem.value.appearance_en || '',
    ion_type_en: selectedItem.value.ion_type_en || '',
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
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
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

function generateMsdsNumber() {
  const year = String(new Date().getFullYear()).slice(-2)
  const seq = String(Math.floor(Math.random() * 100)).padStart(2, '0')
  return `HHJS-${year}${seq}`
}

function showGenerateDialog(lang: 'cn' | 'en') {
  if (!selectedItem.value) return
  generateLanguage.value = lang
  const defaultDate = getDefaultDate()
  const parts = defaultDate.split('/')
  const y = parts[0]
  const m = parts[1]

  generateForm.value = {
    msds_number: generateMsdsNumber(),
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

async function importAllFormulas() {
  if (!validateNewFormulas()) {
    ElMessage.error('存在未填写的必填项，请补齐后再导入')
    return
  }
  for (const formula of newFormulas.value) {
    // composition already pre-parsed on init; use directly
    const composition = formula.composition || []
    
    // Get appearance from orderItems (passed from Phase2Workflow)
    let appearance = formula.appearance || ''
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
        customs_name: formula.customs_name,
        appearance: appearance,
        ion_type: formula.ion_type || '',
        ph: formula.ph || '',
        composition: composition,
      })
    } catch (e) {
      console.error('Failed to import formula:', e)
    }
  }
  ElMessage.success(`已导入 ${newFormulas.value.length} 个新配方`)
  newFormulas.value = []
  showEditList.value = false
  await loadLedger()
  autoSelectMatchingItems()
}

function parseIngredients(ingredients: string): any[] {
  if (!ingredients) return []

  const result: any[] = []

  // Step 1: Normalize
  let text = ingredients
    .replace(/\r\n/g, '\n').replace(/\r/g, '\n')  // normalize line endings
    .replace(/％/g, '%')         // normalize percent sign
    .replace(/：/g, ':')         // normalize colon
    .replace(/；/g, ';')         // normalize semicolon
    .replace(/，/g, ',')         // normalize comma
    .replace(/、/g, ',')         // normalize enum comma
    .replace(/\s+/g, ' ')       // collapse whitespace
    .trim()

  // Remove parenthetical notes like （货源地：江西抚州）
  text = text.replace(/[（(][^）)]*[）)]/g, '').trim()

  // Replace newlines with commas (multi-line = component separators)
  text = text.replace(/\n/g, ',')

  // Step 2: Tokenize the text around CAS numbers and percentages
  // Tokens are: { type: 'text' | 'cas' | 'pct', value: string }
  const RE = /(\d{2,7}-\d{1,2}-\d{1,3})|(\d+(?:\.\d+)?%)/g
  interface Token { type: 'text' | 'cas' | 'pct'; value: string }
  const tokens: Token[] = []

  let lastIdx = 0
  let m: RegExpExecArray | null
  while ((m = RE.exec(text)) !== null) {
    if (m.index > lastIdx) {
      tokens.push({ type: 'text', value: text.slice(lastIdx, m.index) })
    }
    tokens.push({ type: m[1] ? 'cas' : 'pct', value: m[1] || m[2] })
    lastIdx = m.index + m[0].length
  }
  if (lastIdx < text.length) {
    tokens.push({ type: 'text', value: text.slice(lastIdx) })
  }

  // Helper: is a text token purely a separator (punctuation or whitespace)?
  function isSep(val: string): boolean {
    return /^[,:;.\s]+$/.test(val)
  }

  // Step 3: Group tokens into components
  let i = 0
  while (i < tokens.length) {
    const comp = { component_cn: '', component_en: '' as string, cas: '', percentage: '' }

    // --- Extract name (first text token) ---
    if (i < tokens.length && tokens[i].type === 'text') {
      comp.component_cn = tokens[i].value
      i++
    }

    // Skip separator text between name and cas/pct
    while (i < tokens.length && tokens[i].type === 'text' && isSep(tokens[i].value)) {
      i++
    }

    // --- Extract CAS and/or PCT ---
    if (i < tokens.length && tokens[i].type === 'cas') {
      comp.cas = tokens[i].value; i++
      // Skip separator text between CAS and PCT
      while (i < tokens.length && tokens[i].type === 'text' && isSep(tokens[i].value)) { i++ }
      // After CAS, next might be PCT
      if (i < tokens.length && tokens[i].type === 'pct') {
        comp.percentage = tokens[i].value; i++
      }
      // After CAS, next might be another text (component name for next component)
      // Don't consume it here — it starts the next loop iteration
    } else if (i < tokens.length && tokens[i].type === 'pct') {
      comp.percentage = tokens[i].value; i++
      // Skip separator text between PCT and CAS
      while (i < tokens.length && tokens[i].type === 'text' && isSep(tokens[i].value)) { i++ }
      // After PCT, next might be CAS
      if (i < tokens.length && tokens[i].type === 'cas') {
        comp.cas = tokens[i].value; i++
      }
    }

    // Clean up name: trim surrounding separators and leading +
    comp.component_cn = comp.component_cn
      .replace(/^[+,:;.\s]+/, '')
      .replace(/[+,:;.\s]+$/, '')
      .trim()

    // If name is empty but we have cas+pct, use text AFTER pct as name
    if (!comp.component_cn && comp.percentage && !comp.cas) {
      // The pct came before name; look ahead for remaining text tokens
      while (i < tokens.length && tokens[i].type === 'text' && isSep(tokens[i].value)) { i++ }
      if (i < tokens.length && tokens[i].type === 'text') {
        let n = tokens[i].value.replace(/^[+,:;.\s]+/, '').replace(/[+,:;.\s]+$/, '').trim()
        if (n) { comp.component_cn = n; i++ }
      }
    }

    if (comp.component_cn || comp.cas || comp.percentage) {
      result.push(comp)
    }

    // Skip separator tokens between components (e.g. `,` `;` `:` between two components)
    // But NOT text that looks like a component name (preserve it for next iteration)
    while (i < tokens.length && tokens[i].type === 'text' && isSep(tokens[i].value)) {
      i++
    }
  }

  return result
}

// 批量选择相关函数
function toggleBatchMode() {
  batchMode.value = !batchMode.value
  if (!batchMode.value) {
    selectedItems.value = []
  }
  selectedItem.value = null
}

function onSelectionChange(selection: MsdsLedgerItem[]) {
  selectedItems.value = selection
}

function showBatchGenerateDialog() {
  if (selectedItems.value.length === 0) {
    ElMessage.warning('请至少选择一个产品')
    return
  }
  showBatchGenerate.value = true
}

function onBatchGenerated() {
  showBatchGenerate.value = false
  selectedItems.value = []
  loadLedger().then(() => autoSelectMatchingItems())
}

// Auto-select all ledger items matching current order in batch mode
// Auto-select only the ledger items that precisely match each order item
function autoSelectMatchingItems() {
  if (ledgerList.value.length === 0 || orderItemsWithIngredients.value.length === 0) return

  const selectedIds = new Set<number>()
  const itemsToSelect: MsdsLedgerItem[] = []

  for (const orderItem of orderItemsWithIngredients.value) {
    if (!orderItem.customs_name) continue

    // Narrow down candidates by customs_name first
    const candidates = ledgerList.value.filter(
      (item: MsdsLedgerItem) => item.customs_name === orderItem.customs_name
    )
    if (candidates.length === 0) continue

    let matched: MsdsLedgerItem | undefined

    // Match by CAS composition + 含量（CAS 与含量全部一致才匹配，避免选错含量的配方）
    if (!matched && orderItem.customs_ingredients) {
      const parsedComp = parseIngredients(orderItem.customs_ingredients)
      if (parsedComp.length > 0) {
        matched = candidates.find((item: MsdsLedgerItem) => {
          if (!item.composition || item.composition.length === 0) return false
          return compositionMatchLevel(parsedComp, item.composition) === 'full'
        })
      }
    }

    if (matched && !selectedIds.has(matched.id)) {
      selectedIds.add(matched.id)
      itemsToSelect.push(matched)
    }
  }

  if (itemsToSelect.length === 0) return

  batchMode.value = true
  selectedItem.value = null
  nextTick(() => {
    if (tableRef.value) {
      itemsToSelect.forEach(item => {
        tableRef.value.toggleRowSelection(item, true)
      })
    }
  })
}

function onClosed() {
  searchKeyword.value = ''
  ledgerList.value = []
  selectedItem.value = null
  orderItemsNames.value = []
  showEditList.value = false
  importErrors.value = {}
  batchMode.value = false
  selectedItems.value = []
  showBatchGenerate.value = false
}
</script>

<style scoped>
.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.edit-list-section {
  border: 1px solid var(--el-color-warning-light-5);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  background: var(--el-color-warning-light-9);
}
.edit-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.edit-list-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.mismatch-hint {
  font-size: 12px;
  color: var(--el-color-warning);
}
.edit-list-title {
  font-weight: 600;
  color: var(--el-color-warning);
}
.req {
  color: var(--el-color-danger);
}
.formula-edit-card.has-error {
  border-color: var(--el-color-danger);
}
.input-error :deep(.el-input__wrapper),
.input-error :deep(.el-select__wrapper) {
  box-shadow: 0 0 0 1px var(--el-color-danger) inset;
}
.edit-list-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}
.formula-edit-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 12px;
  background: white;
}
.formula-edit-row {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}
.formula-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.formula-field label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.formula-field-wide {
  flex: 3;
}
.formula-actions {
  display: flex;
  justify-content: flex-end;
}
.detail-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.composition-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.composition-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 8px;
}
.composition-table th {
  text-align: left;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  padding: 4px 8px;
  border-bottom: 1px solid var(--el-border-color-light);
}
.composition-table td {
  padding: 4px 4px;
}
.form-error {
  font-size: 12px;
  color: var(--el-color-danger);
  margin-top: 4px;
}
</style>
