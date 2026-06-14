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
        <el-table-column label="托盘数" width="100" align="center">
          <template #default="{ row }">
            <el-input-number
              v-model="row.pallets"
              size="small"
              :min="0"
              controls-position="right"
              class="pallets-input"
              @change="() => onPalletsChange(row)"
            />
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

      <!-- 散货区 -->
      <el-collapse v-if="hasRemainderRows" v-model="showRemainderSection" class="remainder-section">
        <el-collapse-item title="非整板货物统计（需确认装载方式）" name="remainder">
          <div class="remainder-list">
            <template v-for="r in remainderRows" :key="r.id">
              <span v-if="r.remainder > 0" class="remainder-item">{{ r.product_name }}-待处理: {{ r.remainder }}桶</span>
              <span v-else-if="r.remainder < 0" class="remainder-error">{{ r.product_name }}-板数不足: 差 {{ Math.abs(r.remainder) }}桶</span>
            </template>
            <span v-if="totalSignedRemainder > 0" class="remainder-total">合计待处理: {{ totalSignedRemainder }}桶</span>
            <span v-else-if="totalSignedRemainder < 0" class="remainder-error-total">合计不足: 差 {{ Math.abs(totalSignedRemainder) }}桶</span>
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
          <el-button size="small" type="primary" @click="recalcSummary">重新计算汇总</el-button>
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
  pallets: number  // 板数（用户可编辑，作为锚点）
  drums_per_pallet: number
  drums_per_pallet_auto: number  // 自动填的标准值，供比较用
  remainder: number    // drums - pallets*per_pallet（可正可负）
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

const remainderRows = computed(() => rows.value.filter(r => r.remainder !== 0))
const hasRemainderRows = computed(() => rows.value.some(r => r.remainder !== 0))
const totalSignedRemainder = computed(() => rows.value.reduce((s, r) => s + (r.remainder || 0), 0))
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
  // 用户手动修改了板数，重新计算余数和体积/重量
  if (!row.packaging_name || row.drums_per_pallet <= 0) return
  const pkg = packageTypes.value.find(p => p.name === row.packaging_name)
  const pallet = palletTypes.value.find(p => p.name === row.pallet_spec)
  if (!pkg) return

  const loadedDrums = (row.pallets || 0) * row.drums_per_pallet
  row.remainder = (row.drums || 0) - loadedDrums  // 可正可负
  // 体积/重量基于已装载量计算（板数 * 单板贡献 + 余数桶贡献）
  row.total_cbm = loadedDrums * pkg.cbm + (row.remainder > 0 ? row.remainder * pkg.cbm : 0)
  row.total_weight_kg = loadedDrums * pkg.gross_kg + (row.remainder > 0 ? row.remainder * pkg.tare_kg : 0)
  if (pallet && row.remainder > 0) {
    // 余数单独打板时，加一整卡板的体积和重量
    row.total_cbm += pallet.cbm
    row.total_weight_kg += pallet.weight_kg
  }
  row.fits_20gp = row.total_cbm <= 28 && row.total_weight_kg <= 21000
  row.fits_40gp = row.total_cbm <= 67 && row.total_weight_kg <= 27000
  recalcSummary()
}

function calcRemainderContribution(): { extraCbm: number; extraWeight: number } {
  let extraCbm = 0
  let extraWeight = 0
  for (const r of rows.value) {
    if (r.remainder <= 0) continue
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
  // 用户手动修改了每卡板桶数，按实际值重新计算
  if (!row.packaging_name || row.quantity_kg <= 0 || row.drums_per_pallet <= 0) return
  const pkg = packageTypes.value.find(p => p.name === row.packaging_name)
  if (!pkg) return

  const drums = Math.ceil(row.quantity_kg / pkg.net_kg)
  row.drums = drums
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
    row.drums = 0; row.pallets = 0; row.drums_per_pallet = 0; row.full_pallets = 0; row.remainder = 0
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

function recalcSummary() {
  const { extraCbm, extraWeight } = calcRemainderContribution()
  const s = { total_drums: 0, total_pallets: 0, total_cbm: 0, total_weight_kg: 0, fits_20gp: true, fits_40gp: true }
  for (const r of rows.value) {
    s.total_drums += r.drums || 0
    // pallets 列就是用户想要的板数（已含用户手动修改）
    s.total_pallets += r.pallets || 0
    s.total_cbm += r.total_cbm || 0
    s.total_weight_kg += r.total_weight_kg || 0
    if (!r.fits_20gp) s.fits_20gp = false
    if (!r.fits_40gp) s.fits_40gp = false
  }
  // 按整板计算时，每个 remainder>0 的行额外加1个卡板（余数单独打板）
  s.total_pallets += remainder_mode.value === 'full_pallet'
    ? rows.value.filter(r => r.remainder > 0).length
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
.pallets-input { width: 90px; }
.remainder-section { margin-top: 8px; }
.remainder-list { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.remainder-item { font-size: 13px; color: #e6a23c; }
.remainder-error { font-size: 13px; color: #f56c6c; font-weight: 600; }
.remainder-total { font-size: 13px; font-weight: 600; color: #f56c6c; }
.remainder-error-total { font-size: 13px; font-weight: 600; color: #f56c6c; }
.remainder-mode { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.mode-label { font-size: 13px; color: #606266; }
.remainder-contribution { font-size: 13px; color: #409eff; margin-bottom: 8px; }
</style>
