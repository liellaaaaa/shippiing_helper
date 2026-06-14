<template>
  <div class="packaging-calculator">
    <div class="calc-table-wrapper">
      <!-- 表头工具栏 -->
      <div class="calc-toolbar">
        <el-button size="small" @click="addRow">+ 添加产品</el-button>
      </div>

      <!-- 多行计算表格 -->
      <el-table :data="rows" border size="small" class="calc-table">
        <el-table-column label="产品" width="150">
          <template #default="{ row }">
            <el-select v-model="row.product_name" placeholder="选择产品" size="small" filterable allow-create>
              <el-option v-for="p in productOptions" :key="p" :label="p" :value="p" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="包装种类" width="220">
          <template #default="{ row }">
            <el-select v-model="row.packaging_name" placeholder="选择包装" size="small" filterable popper-class="pkg-select-popper" @change="(val: string) => onRowPackageChange(row, val)">
              <el-option v-for="p in packageTypes" :key="p.name" :label="p.name" :value="p.name">
                <span class="pkg-opt">{{ p.name }}</span>
                <span class="pkg-dims">{{ p.dims }}</span>
              </el-option>
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="卡板规格" width="140">
          <template #default="{ row }">
            <el-select v-model="row.pallet_spec" placeholder="选择托盘" size="small" :disabled="!row.packaging_name" @change="() => onRowPackageChange(row, row.packaging_name)">
              <el-option v-for="p in palletTypes" :key="p.name" :label="p.name" :value="p.name" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="数量(kg)" width="120">
          <template #default="{ row }">
            <el-input-number v-model="row.quantity_kg" size="small" :min="0" controls-position="right" @change="() => onRowPackageChange(row, row.packaging_name)" />
          </template>
        </el-table-column>
        <el-table-column label="每卡板桶数" width="100">
          <template #default="{ row }">
            <el-input-number
              v-model="row.drums_per_pallet"
              size="small"
              :min="1"
              controls-position="right"
              class="drums-per-pallet-input"
              @change="() => onRowCapacityChange(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="桶数" width="70" align="center">
          <template #default="{ row }"><span>{{ row.drums || '-' }}</span></template>
        </el-table-column>
        <el-table-column label="板数" width="130" align="center">
          <template #default="{ row }">
            <div class="pallets-cell">
              <el-input-number
                v-model="row.pallets"
                size="small"
                :min="0"
                controls-position="right"
                class="pallets-input"
                @change="() => onPalletsChange(row)"
              />
              <span v-if="row.is_auto" class="pallets-badge auto">建议</span>
              <span v-else-if="getPalletsFeedback(row).type === 'surplus'" class="pallets-badge surplus">
                富余{{ getPalletsFeedback(row).text }}
              </span>
              <span v-else-if="getPalletsFeedback(row).type === 'shortfall'" class="pallets-badge shortfall">
                不足差{{ getPalletsFeedback(row).text }}
              </span>
            </div>
            <div v-if="row.is_auto === false && row.pallets * row.drums_per_pallet < row.drums" class="pallets-warning">
              ⚠️ 当前板数仅能装 {{ row.pallets * row.drums_per_pallet }} 桶，还有 {{ row.drums - row.pallets * row.drums_per_pallet }} 桶未安排
            </div>
          </template>
        </el-table-column>
        <el-table-column label="总体积" width="90" align="center">
          <template #default="{ row }"><span>{{ row.total_cbm ? row.total_cbm.toFixed(3) : '-' }}</span></template>
        </el-table-column>
        <el-table-column label="总毛重" width="90" align="center">
          <template #default="{ row }"><span>{{ row.total_weight_kg ? row.total_weight_kg.toFixed(1) : '-' }}</span></template>
        </el-table-column>
        <el-table-column label="20GP" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.fits_20gp ? 'success' : 'info'" size="small">{{ row.fits_20gp ? '✅' : '❌' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="60">
          <template #default="{ $index }">
            <el-button text type="danger" size="small" @click="removeRow($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 汇总行 -->
      <div v-if="rows.length > 0" class="calc-summary">
        <el-divider content-position="left">包装汇总</el-divider>
        <el-descriptions :column="5" border size="small">
          <el-descriptions-item label="总桶数"><strong>{{ summary.total_drums }}</strong></el-descriptions-item>
          <el-descriptions-item label="总托盘数"><strong>{{ summary.total_pallets }}</strong></el-descriptions-item>
          <el-descriptions-item label="总体积(CBM)"><strong>{{ summary.total_cbm.toFixed(3) }}</strong></el-descriptions-item>
          <el-descriptions-item label="总毛重(kg)"><strong>{{ summary.total_weight_kg.toFixed(1) }}</strong></el-descriptions-item>
          <el-descriptions-item label="货柜判断">
            <el-tag :type="summary.fits_20gp ? 'success' : summary.fits_40gp ? 'warning' : 'danger'" size="small">
              {{ summary.fits_20gp ? '20GP ✅' : summary.fits_40gp ? '40GP ✅' : '超出' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 散货区（仅在自动模式有余数时显示） -->
      <el-collapse v-if="hasAutoRemainderRows" v-model="showRemainderSection" class="remainder-section">
        <el-collapse-item title="非整板货物统计（需确认装载方式）" name="remainder">
          <div class="remainder-list">
            <span v-for="r in autoRemainderRows" :key="r.id" class="remainder-item">
              {{ r.product_name }}-待处理: {{ r.remainder }}桶
            </span>
            <span class="remainder-total">合计待处理: {{ totalAutoRemainder }}桶</span>
          </div>
          <div class="remainder-mode">
            <span class="mode-label">散货装载计算模式：</span>
            <el-radio-group v-model="remainder_mode" size="small">
              <el-radio-button value="full_pallet">按整板计算</el-radio-button>
              <el-radio-button value="actual_stacked">按实际堆叠</el-radio-button>
              <el-radio-button value="loose">散货混装</el-radio-button>
            </el-radio-group>
          </div>
          <div class="remainder-contribution">
            散货贡献：+{{ remainderExtraCbm.toFixed(3) }} CBM | +{{ remainderExtraWeight.toFixed(1) }} kg
          </div>
          <el-button size="small" type="primary" @click="applyRemainderMode">应用并重新计算</el-button>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import packagingApi, { type PackageType, type PalletType } from '@/api/packaging'

// Task 3A: PackingRow interface
interface PackingRow {
  id: string
  internal_code: string
  product_name: string
  packaging_name: string
  pallet_spec: string
  quantity_kg: number
  drums: number
  pallets: number  // 板数（用户可编辑）
  drums_per_pallet: number
  drums_per_pallet_auto: number  // 自动填的标准值，供比较用
  remainder: number    // drums - floor(drums/per_pallet)*per_pallet（仅自动模式有效）
  is_auto: boolean   // true=系统自动算板数；false=用户手动修改过
  total_cbm: number
  total_weight_kg: number
  fits_20gp: boolean
  fits_40gp: boolean
}

// Task 3A: Replace result with rows array
const packageTypes = ref<PackageType[]>([])
const palletTypes = ref<PalletType[]>([])
const productOptions = ref<string[]>([])
const rows = ref<PackingRow[]>([])
const summary = ref({ total_drums: 0, total_pallets: 0, total_cbm: 0, total_weight_kg: 0, fits_20gp: false, fits_40gp: false })
const remainder_mode = ref<'full_pallet' | 'actual_stacked' | 'loose'>('actual_stacked')
const showRemainderSection = ref(true)

const remainderRows = computed(() => rows.value.filter(r => r.remainder > 0 && r.is_auto))
const hasAutoRemainderRows = computed(() => rows.value.some(r => r.remainder > 0 && r.is_auto))
const autoRemainderRows = computed(() => rows.value.filter(r => r.remainder > 0 && r.is_auto))
const totalAutoRemainder = computed(() => rows.value.reduce((s, r) => s + (r.remainder > 0 && r.is_auto ? r.remainder : 0), 0))
const remainderExtraCbm = computed(() => calcRemainderContribution().extraCbm)
const remainderExtraWeight = computed(() => calcRemainderContribution().extraWeight)

onMounted(async () => {
  try {
    const [pkgs, pallets] = await Promise.all([
      packagingApi.getTypes(),
      packagingApi.getPallets(),
    ])
    packageTypes.value = pkgs
    palletTypes.value = pallets
  } catch (e) {
    console.error('加载包装数据失败', e)
  }
})

// Task 3C: Row operation functions
function addRow(internalCode = '', productName = '', quantityKg = 0) {
  rows.value.push({
    id: Date.now().toString(),
    internal_code: internalCode,
    product_name: productName,
    packaging_name: '',
    pallet_spec: '1.1*1.1m',
    quantity_kg: quantityKg,
    drums: 0,
    pallets: 0,
    drums_per_pallet: 0,
    drums_per_pallet_auto: 0,
    remainder: 0,
    is_auto: true,
    total_cbm: 0,
    total_weight_kg: 0,
    fits_20gp: false,
    fits_40gp: false,
  })
  if (productName) {
    if (!productOptions.value.includes(productName)) {
      productOptions.value.push(productName)
    }
  }
}

function removeRow(index: number) {
  rows.value.splice(index, 1)
  recalcSummary()
}

function onPalletsChange(row: PackingRow) {
  // 用户手动修改了板数，标记为手动模式，重新计算体积/重量
  if (!row.packaging_name || row.drums_per_pallet <= 0) return
  const pkg = packageTypes.value.find(p => p.name === row.packaging_name)
  const pallet = palletTypes.value.find(p => p.name === row.pallet_spec)
  if (!pkg) return

  row.is_auto = false  // 标记为手动模式
  const capacity = (row.pallets || 0) * row.drums_per_pallet
  const shortfall = (row.drums || 0) - capacity

  // 体积/重量基于用户指定的板数计算（不含未装载部分）
  row.total_cbm = capacity * pkg.cbm
  row.total_weight_kg = capacity * pkg.gross_kg
  if (pallet) {
    row.total_cbm += (row.pallets || 0) * pallet.cbm
    row.total_weight_kg += (row.pallets || 0) * pallet.weight_kg
  }
  row.fits_20gp = row.total_cbm <= 28 && row.total_weight_kg <= 21000
  row.fits_40gp = row.total_cbm <= 67 && row.total_weight_kg <= 27000
  recalcSummary()
}

function calcRemainderContribution(): { extraCbm: number; extraWeight: number } {
  let extraCbm = 0
  let extraWeight = 0
  for (const r of rows.value) {
    // 仅对自动模式且有余数的行计算
    if (r.remainder <= 0 || !r.is_auto) continue
    const pkg = packageTypes.value.find(p => p.name === r.packaging_name)
    const pallet = palletTypes.value.find(p => p.name === r.pallet_spec)
    if (!pkg) continue

    if (remainder_mode.value === 'full_pallet') {
      extraCbm += (pallet?.cbm ?? 0)
      extraWeight += r.remainder * pkg.tare_kg + (pallet?.weight_kg ?? 0)
    } else if (remainder_mode.value === 'actual_stacked') {
      extraCbm += r.remainder * pkg.cbm
      extraWeight += r.remainder * pkg.tare_kg
    } else {
      extraCbm += r.remainder * pkg.cbm
      extraWeight += r.remainder * pkg.net_kg
    }
  }
  return { extraCbm, extraWeight }
}

async function onRowCapacityChange(row: PackingRow) {
  // 用户手动修改了每卡板桶数，按实际值重新计算（自动模式）
  if (!row.packaging_name || row.quantity_kg <= 0 || row.drums_per_pallet <= 0) return
  const pkg = packageTypes.value.find(p => p.name === row.packaging_name)
  if (!pkg) return

  const drums = Math.ceil(row.quantity_kg / pkg.net_kg)
  row.drums = drums
  row.is_auto = true  // 恢复自动模式
  const fp = Math.floor(drums / row.drums_per_pallet)
  row.pallets = fp
  row.remainder = drums - fp * row.drums_per_pallet
  row.total_cbm = drums * pkg.cbm
  row.total_weight_kg = drums * pkg.gross_kg + fp * 20
  row.fits_20gp = row.total_cbm <= 28 && row.total_weight_kg <= 21000
  row.fits_40gp = row.total_cbm <= 67 && row.total_weight_kg <= 27000
  recalcSummary()
}

async function onRowPackageChange(row: PackingRow, packagingName: string) {
  if (!packagingName || row.quantity_kg <= 0) {
    row.drums = 0; row.pallets = 0; row.drums_per_pallet = 0; row.remainder = 0
    row.is_auto = true
    row.total_cbm = 0; row.total_weight_kg = 0; row.fits_20gp = false; row.fits_40gp = false
    recalcSummary()
    return
  }
  try {
    const pkg = packageTypes.value.find(p => p.name === packagingName)
    const schemes = await packagingApi.calculateSchemes({
      packaging_name: packagingName,
      order_qty_kg: row.quantity_kg,
      use_pallet: !!row.pallet_spec,
    })
    const match = schemes.find((s: any) => s.pallet_type === row.pallet_spec) || schemes[0]
    if (match) {
      row.drums = match.drums
      const fp = match.full_pallets ?? Math.floor(match.drums / match.drums_per_pallet)
      row.pallets = fp
      row.remainder = match.remainder ?? (match.drums - fp * match.drums_per_pallet)
      row.drums_per_pallet = match.drums_per_pallet
      row.total_cbm = match.total_cbm
      row.total_weight_kg = match.total_weight_kg
      row.fits_20gp = match.fits_20gp
      row.fits_40gp = match.fits_40gp
      row.is_auto = true  // 恢复自动模式
    }
    // 自动填标准容量（只有用户没手动改过时才填）
    if (pkg && (!row.drums_per_pallet || row.drums_per_pallet === row.drums_per_pallet_auto)) {
      const is1x1 = row.pallet_spec && row.pallet_spec.includes('1.0*1.0')
      row.drums_per_pallet_auto = is1x1 ? (pkg.pallet_qty_1x1 ?? 0) : (pkg.pallet_qty_1_1x1_1 ?? 0)
      row.drums_per_pallet = row.drums_per_pallet_auto
    }
    recalcSummary()
  } catch (e) {
    console.error('行计算失败', e)
  }
}

function getPalletsFeedback(row: PackingRow): { type: 'surplus' | 'shortfall' | 'ok'; text: string } {
  if (row.is_auto) return { type: 'ok', text: '' }
  const capacity = (row.pallets || 0) * row.drums_per_pallet
  const drums = row.drums || 0
  if (capacity >= drums) {
    return { type: 'surplus', text: `(可装${capacity}桶)` }
  } else {
    return { type: 'shortfall', text: `${drums - capacity}桶` }
  }
}

function applyRemainderMode() {
  // 按整板计算：把每个自动模式有余数的行的板数 +1，余数清零
  for (const r of rows.value) {
    if (r.remainder > 0 && r.is_auto) {
      r.pallets = (r.pallets || 0) + 1
      r.remainder = 0
      r.is_auto = false  // 转为手动模式
    }
  }
  recalcSummary()
}

function recalcSummary() {
  const { extraCbm, extraWeight } = calcRemainderContribution()
  const s = { total_drums: 0, total_pallets: 0, total_cbm: 0, total_weight_kg: 0, fits_20gp: true, fits_40gp: true }
  for (const r of rows.value) {
    s.total_drums += r.drums || 0
    s.total_pallets += r.pallets || 0
    s.total_cbm += r.total_cbm || 0
    s.total_weight_kg += r.total_weight_kg || 0
    if (!r.fits_20gp) s.fits_20gp = false
    if (!r.fits_40gp) s.fits_40gp = false
  }
  // 按整板计算时，仅对自动模式有余数的行额外加1个卡板
  s.total_pallets += remainder_mode.value === 'full_pallet'
    ? rows.value.filter(r => r.remainder > 0 && r.is_auto).length
    : 0
  s.total_cbm += extraCbm
  s.total_weight_kg += extraWeight
  summary.value = s
}

function clearRows() {
  rows.value = []
  summary.value = { total_drums: 0, total_pallets: 0, total_cbm: 0, total_weight_kg: 0, fits_20gp: false, fits_40gp: false }
}

function getSummary() {
  return summary.value
}

function getRows() {
  // 返回每行的包装计算结果，供保存时使用
  return rows.value.map(r => ({
    internal_code: r.internal_code || r.product_name,  // 优先用 internal_code（如 CF253E）
    product_name: r.product_name,
    packaging_name: r.packaging_name,
    pallet_spec: r.pallet_spec,
    drums: r.drums,
    pallets: r.pallets,
    drums_per_pallet: r.drums_per_pallet,
    net_weight_kg: 0,
    gross_weight_kg: r.total_weight_kg,
    volume_cbm: r.total_cbm,
    fits_20gp: r.fits_20gp ? '适合' : '超出',
  }))
}

// Task 3D: Backward compatibility functions for parent component
function setQuantity(kg: number) {
  if (rows.value.length > 0) {
    rows.value[0].quantity_kg = kg
    if (rows.value[0].packaging_name) {
      onRowPackageChange(rows.value[0], rows.value[0].packaging_name)
    }
  }
}

function selectPackage(name: string) {
  if (rows.value.length > 0) {
    rows.value[0].packaging_name = name
  }
}

// Task 3D: Update defineExpose
defineExpose({ addRow, clearRows, setQuantity, selectPackage, getSummary, getRows })
</script>

<style scoped>
/* Task 3E: Updated CSS */
.packaging-calculator { padding: 4px 0; }
.calc-table-wrapper { padding: 4px 0; overflow-x: auto; }
.calc-toolbar { margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.calc-table { margin-bottom: 12px; }
.calc-summary { margin-top: 8px; }
.pkg-select-popper { min-width: 320px !important; }
.pkg-opt { font-weight: 500; }
.pkg-dims { font-size: 12px; color: #909399; margin-left: 8px; }
.drums-per-pallet-input { width: 80px; }
.pallets-input { width: 80px; }
.pallets-cell { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.pallets-badge { font-size: 11px; font-weight: 500; }
.pallets-badge.auto { color: #909399; }
.pallets-badge.surplus { color: #67c23a; }
.pallets-badge.shortfall { color: #f56c6c; }
.pallets-warning { font-size: 11px; color: #f56c6c; white-space: nowrap; margin-top: 2px; }
.remainder-section { margin-top: 8px; }
.remainder-list { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.remainder-item { font-size: 13px; color: #e6a23c; }
.remainder-total { font-size: 13px; font-weight: 600; color: #f56c6c; }
.remainder-mode { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.mode-label { font-size: 13px; color: #606266; }
.remainder-contribution { font-size: 13px; color: #409eff; margin-bottom: 8px; }
</style>
