<template>
  <div class="packaging-calculator">
    <div class="calc-table-wrapper">
      <!-- 货柜选择栏 -->
      <div class="container-selector-bar">
        <span class="toolbar-label">货柜选择：</span>
        <el-radio-group v-model="containerType" size="small">
          <el-radio-button value="none">不装柜</el-radio-button>
          <el-radio-button value="20gp">20GP</el-radio-button>
          <el-radio-button value="40gp">40GP</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 多行计算表格 -->
      <el-table :data="rows" border size="small" class="calc-table">
        <el-table-column label="产品" width="150">
          <template #default="{ row }">
            <el-select v-model="row.product_name" placeholder="选择产品" size="small" filterable allow-create @change="(val: string) => onRowProductChange(row, val)">
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
            <el-select v-model="row.pallet_spec" placeholder="选择托盘/不打卡板" size="small" :disabled="!row.packaging_name" @change="() => onRowPackageChange(row, row.packaging_name)">
              <!-- "不打卡板"选项，始终可用，value="" -->
              <el-option label="不打卡板" value="" />
              <el-option
                v-for="p in palletTypes"
                :key="p.name"
                :label="p.name"
                :value="p.name"
                :disabled="isPalletUnsupported(row.packaging_name, p.name)"
              />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="数量(kg)" width="120">
          <template #default="{ row }">
            <el-input-number v-model="row.quantity_kg" size="small" :min="0" controls-position="right" @change="() => onRowPackageChange(row, row.packaging_name)" />
          </template>
        </el-table-column>
        <el-table-column label="实际装入量(kg)" width="130">
          <template #default="{ row }">
            <el-input-number
              v-model="row.actual_fill_kg"
              size="small"
              :min="0"
              :step="1"
              controls-position="right"
              :placeholder="getNetKg(row.packaging_name)"
              @change="() => onRowPackageChange(row, row.packaging_name)"
            />
          </template>
        </el-table-column>
        <el-table-column label="每卡板桶数" width="100">
          <template #default="{ row }">
            <template v-if="isPalletizable(row.packaging_name) && row.pallet_spec !== ''">
              <el-input-number
                v-model="row.drums_per_pallet"
                size="small"
                :min="1"
                controls-position="right"
                class="drums-per-pallet-input"
                @change="() => onRowCapacityChange(row)"
              />
            </template>
            <span v-else style="color:#999;font-size:12px">—</span>
          </template>
        </el-table-column>
        <el-table-column label="桶数" width="70" align="center">
          <template #default="{ row }"><span>{{ row.drums || '-' }}</span></template>
        </el-table-column>
        <el-table-column label="板数" width="130" align="center">
          <template #default="{ row }">
            <template v-if="isPalletizable(row.packaging_name) && row.pallet_spec !== ''">
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
            <span v-else style="color:#999;font-size:12px">—</span>
          </template>
        </el-table-column>
        <el-table-column label="总体积" width="100" align="center">
          <template #default="{ row }">
            <el-input-number
              v-model="row.volume_override"
              size="small"
              :min="0"
              :step="0.001"
              :precision="3"
              controls-position="right"
              placeholder="实测"
              style="width: 90px"
              @change="() => onVolumeChange(row)"
            />
            <div class="calc-hint">计 {{ row.total_cbm ? (row.volume_override ?? row.total_cbm).toFixed(3) : '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="总毛重" width="90" align="center">
          <template #default="{ row }"><span>{{ row.total_weight_kg ? row.total_weight_kg.toFixed(1) : '-' }}</span></template>
        </el-table-column>
        <el-table-column :label="containerType === 'none' ? '货柜' : containerType.toUpperCase()" width="70" align="center">
          <template #default="{ row }">
            <el-tag v-if="containerType === 'none'" type="info" size="small">—</el-tag>
            <el-tag v-else-if="containerType === '20gp'" :type="row.fits_20gp ? 'success' : 'info'" size="small">
              {{ row.fits_20gp ? '✅' : '❌' }}
            </el-tag>
            <el-tag v-else :type="row.fits_40gp ? 'success' : 'warning'" size="small">
              {{ row.fits_40gp ? '✅' : '❌' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="60">
          <template #default="{ $index }">
            <el-button text type="danger" size="small" @click="removeRow($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 添加产品 -->
      <div class="calc-toolbar">
        <el-button size="small" @click="addRow">+ 添加产品</el-button>
      </div>

      <!-- 汇总行 -->
      <div v-if="rows.length > 0" class="calc-summary">
        <el-divider content-position="left">包装汇总</el-divider>
        <el-descriptions :column="5" border size="small">
          <el-descriptions-item label="总桶数"><strong>{{ summary.total_drums }}</strong></el-descriptions-item>
          <el-descriptions-item label="总托盘数"><strong>{{ summary.total_pallets }}</strong></el-descriptions-item>
          <el-descriptions-item label="总体积(CBM)"><strong>{{ summary.total_cbm.toFixed(3) }}</strong></el-descriptions-item>
          <el-descriptions-item label="总毛重(kg)"><strong>{{ summary.total_weight_kg.toFixed(1) }}</strong></el-descriptions-item>
          <el-descriptions-item label="货柜判断">
            <el-tag :type="getContainerTagType()" size="small">{{ getContainerLabel() }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 尾板提示 / 合板 -->
      <el-collapse v-if="hasAutoRemainderRows" v-model="showRemainderSection" class="remainder-section">
        <el-collapse-item title="尾板货物（托数已含尾板，可选合板）" name="remainder">
          <div class="remainder-list">
            <div v-for="r in autoRemainderRows" :key="r.id" class="remainder-row-item">
              <span class="remainder-name">{{ r.product_name }}-尾板: {{ r.remainder }} 件（已计入板数 {{ r.pallets }}）</span>
            </div>
            <span class="remainder-total">合计尾板: {{ totalAutoRemainder }} 件</span>
          </div>
          <div class="remainder-mode">
            <span class="mode-label">装载方式：</span>
            <el-radio-group v-model="remainder_mode" size="small">
              <el-radio-button value="full_pallet_independent">独立开托（默认）</el-radio-button>
              <el-radio-button value="full_pallet_merge">合板</el-radio-button>
              <el-radio-button value="no_pallet">不打卡板</el-radio-button>
            </el-radio-group>
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
  actual_fill_kg: number | null  // 每桶实际装入量，null=用标称值
  drums: number
  pallets: number  // 板数（用户可编辑）
  drums_per_pallet: number
  drums_per_pallet_auto: number  // 自动填的标准值，供比较用
  remainder: number    // 尾板件数（展示用，托数已含尾板）
  is_auto: boolean   // true=系统自动算板数；false=用户手动修改过
  remainder_pallet_spec: string  // 余数板规格（默认1.0*1.0m）
  total_cbm: number
  volume_override: number | null  // 实测体积覆盖
  total_weight_kg: number
  fits_20gp: boolean
  fits_40gp: boolean
}

// Task 3A: Replace result with rows array
const packageTypes = ref<PackageType[]>([])
const palletTypes = ref<PalletType[]>([])
const productOptions = ref<string[]>([])
// 产品名 → 内部编码 映射（预填行注册，用户加行选产品时自动带出编码）
const codeMap = ref<Record<string, string>>({})
const rows = ref<PackingRow[]>([])
const summary = ref({ total_drums: 0, total_pallets: 0, total_cbm: 0, total_weight_kg: 0, fits_20gp: false, fits_40gp: false })
const remainder_mode = ref<'full_pallet_merge' | 'full_pallet_independent' | 'no_pallet'>('full_pallet_independent')
const showRemainderSection = ref('remainder')
const containerType = ref<'none' | '20gp' | '40gp'>('20gp')

function getContainerTagType(): string {
  if (containerType.value === 'none') return 'info'
  if (containerType.value === '20gp') return summary.value.fits_20gp ? 'success' : 'danger'
  return summary.value.fits_40gp ? 'success' : 'warning'
}

function getContainerLabel(): string {
  if (containerType.value === 'none') return '不装柜 ✅'
  if (containerType.value === '20gp') return summary.value.fits_20gp ? '20GP ✅' : '20GP ❌'
  return summary.value.fits_40gp ? '40GP ✅' : '40GP ❌'
}

const remainderRows = computed(() => rows.value.filter(r => r.remainder > 0 && r.is_auto))
const hasAutoRemainderRows = computed(() => rows.value.some(r => r.remainder > 0 && r.is_auto))
const autoRemainderRows = computed(() => rows.value.filter(r => r.remainder > 0 && r.is_auto))
const totalAutoRemainder = computed(() => rows.value.reduce((s, r) => s + (r.remainder > 0 && r.is_auto ? r.remainder : 0), 0))
const mergePalletCount = ref(0)

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
  if (internalCode && productName) {
    codeMap.value[productName] = internalCode
  }
  rows.value.push({
    id: Date.now().toString(),
    internal_code: internalCode,
    product_name: productName,
    packaging_name: '',
    pallet_spec: '1.1*1.1m',
    quantity_kg: quantityKg,
    actual_fill_kg: null,
    drums: 0,
    pallets: 0,
    drums_per_pallet: 0,
    drums_per_pallet_auto: 0,
    remainder: 0,
    is_auto: true,
    remainder_pallet_spec: '1.0*1.0m',
    total_cbm: 0,
    volume_override: null,
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

function onRowProductChange(row: PackingRow, name: string) {
  // 用户加行选产品时自动带出内部编码（保存时按编码配对，拆行才能各自入库）
  row.internal_code = codeMap.value[name] || ''
}

/** 统一重算一行：毛重=净+桶皮+托盘，体积=件×桶CBM+托×托CBM（按件数，禁止板位口径） */
function recalcRow(row: PackingRow) {
  const pkg = packageTypes.value.find(p => p.name === row.packaging_name)
  if (!pkg) return
  const fill = row.actual_fill_kg && row.actual_fill_kg > 0 ? row.actual_fill_kg : pkg.net_kg
  const qty = row.quantity_kg || 0
  const drums = row.drums > 0 ? row.drums : (fill > 0 ? Math.ceil(qty / fill) : 0)
  row.drums = drums
  const drumTare = drums * pkg.tare_kg
  const drumCbm = drums * pkg.cbm
  let palTare = 0
  let palCbm = 0
  if (row.pallet_spec && pkg.is_palletizable !== false) {
    const pal = palletTypes.value.find(p => p.name === row.pallet_spec)
    if (pal && row.pallets > 0) {
      palTare = row.pallets * pal.weight_kg
      palCbm = row.pallets * pal.cbm
    }
  }
  // 毛重 = 净含量 + 桶皮 + 托盘
  row.total_weight_kg = qty + drumTare + palTare
  row.total_cbm = row.volume_override ?? (drumCbm + palCbm)
  row.fits_20gp = row.total_cbm <= 28 && row.total_weight_kg <= 21000
  row.fits_40gp = row.total_cbm <= 67 && row.total_weight_kg <= 27000
}

function onPalletsChange(row: PackingRow) {
  // 手改托数 = 少用/不用托；货载体积毛重仍按实际件数
  if (!row.packaging_name) return
  row.is_auto = false
  row.pallets = Math.max(0, row.pallets || 0)
  recalcRow(row)
  recalcSummary()
}

function onVolumeChange(row: PackingRow) {
  // 实测体积覆盖
  if (row.volume_override !== null && row.volume_override !== undefined) {
    row.total_cbm = row.volume_override
  } else {
    recalcRow(row)
  }
  row.fits_20gp = row.total_cbm <= 28 && row.total_weight_kg <= 21000
  row.fits_40gp = row.total_cbm <= 67 && row.total_weight_kg <= 27000
  recalcSummary()
}

/** 合板时额外托贡献：只加托体积/托重，禁止再加桶皮（件数已在行内） */
function calcRemainderContribution(): { extraCbm: number; extraWeight: number } {
  let extraCbm = 0
  let extraWeight = 0
  if (remainder_mode.value === 'no_pallet') return { extraCbm, extraWeight }

  const remainderRows = rows.value.filter(r => r.remainder > 0 && r.is_auto)

  if (remainder_mode.value === 'full_pallet_merge') {
    const groups = new Map<string, { totalDrums: number; capacity: number; palletSpec: string }>()
    for (const r of remainderRows) {
      const pkg = packageTypes.value.find(p => p.name === r.packaging_name)
      if (!pkg) continue
      const capacity = r.remainder_pallet_spec.includes('1.0*1.0')
        ? ((pkg as any).pallet_qty_1x1 ?? 0)
        : ((pkg as any).pallet_qty_1_1x1_1 ?? 0)
      const key = `${r.remainder_pallet_spec}|${capacity}`
      if (!groups.has(key)) groups.set(key, { totalDrums: 0, capacity, palletSpec: r.remainder_pallet_spec })
      groups.get(key)!.totalDrums += r.remainder
    }
    for (const [, g] of groups) {
      if (g.capacity <= 0 || g.totalDrums <= 0) continue
      const boards = Math.ceil(g.totalDrums / g.capacity)
      const pallet = palletTypes.value.find(p => p.name === g.palletSpec)
      if (pallet) {
        extraCbm += boards * pallet.cbm
        extraWeight += boards * pallet.weight_kg
      }
    }
  } else if (remainder_mode.value === 'full_pallet_independent') {
    for (const r of remainderRows) {
      const pallet = palletTypes.value.find(p => p.name === r.remainder_pallet_spec)
      if (!pallet) continue
      extraCbm += pallet.cbm
      extraWeight += pallet.weight_kg
    }
  }
  return { extraCbm, extraWeight }
}

async function onRowCapacityChange(row: PackingRow) {
  if (!row.packaging_name || row.quantity_kg <= 0 || row.drums_per_pallet <= 0) return
  const pkg = packageTypes.value.find(p => p.name === row.packaging_name)
  if (!pkg) return

  const fillKg = row.actual_fill_kg && row.actual_fill_kg > 0 ? row.actual_fill_kg : pkg.net_kg
  row.drums = Math.ceil(row.quantity_kg / fillKg)
  row.is_auto = true
  const fp = Math.floor(row.drums / row.drums_per_pallet)
  const rem = row.drums % row.drums_per_pallet
  row.remainder = rem
  // 托数含尾板
  row.pallets = fp + (rem ? 1 : 0)
  recalcRow(row)
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
    const usePallet = isPalletizable(packagingName) && !!row.pallet_spec
    if (!isPalletizable(packagingName)) {
      row.pallet_spec = ''
    }
    const schemes = await packagingApi.calculateSchemes({
      packaging_name: packagingName,
      order_qty_kg: row.quantity_kg,
      use_pallet: usePallet,
      actual_fill_kg: row.actual_fill_kg && row.actual_fill_kg > 0 ? row.actual_fill_kg : undefined,
    })
    const match = schemes.find((s: any) => s.pallet_type === row.pallet_spec) || schemes[0]
    if (match) {
      row.drums = match.drums
      row.drums_per_pallet = match.drums_per_pallet
      row.pallets = match.pallets // 含尾板
      row.remainder = match.remainder ?? 0
      row.is_auto = true
      row.remainder_pallet_spec = '1.0*1.0m'
      row.volume_override = null
      recalcRow(row)
    }
    // 自动填标准容量（只有后端未返回有效值 且 用户未手动改过时才填）
    if (pkg && row.drums_per_pallet === 0 && row.drums_per_pallet_auto === 0) {
      const is1x1 = row.pallet_spec && row.pallet_spec.includes('1.0*1.0')
      row.drums_per_pallet_auto = is1x1 ? (pkg.pallet_qty_1x1 ?? 0) : (pkg.pallet_qty_1_1x1_1 ?? 0)
      row.drums_per_pallet = row.drums_per_pallet_auto
    }
    recalcSummary()
  } catch (e) {
    console.error('行计算失败', e)
  }
}

function isPalletizable(packagingName: string): boolean {
  if (!packagingName) return true
  const pkg = packageTypes.value.find(p => p.name === packagingName)
  if (!pkg) return true
  return (pkg as any).is_palletizable !== false
}

function isPalletUnsupported(packagingName: string, palletName: string): boolean {
  if (!packagingName) return false
  if (!isPalletizable(packagingName)) return true
  const pkg = packageTypes.value.find(p => p.name === packagingName)
  if (!pkg) return false
  if (palletName.includes('1.0*1.0')) {
    return (pkg as any).pallet_qty_1x1 == null
  }
  return (pkg as any).pallet_qty_1_1x1_1 == null
}

function getNetKg(packagingName: string): string {
  if (!packagingName) return ''
  const pkg = packageTypes.value.find(p => p.name === packagingName)
  return pkg ? String(pkg.net_kg) : ''
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
  const remRows = rows.value.filter(r => r.remainder > 0 && r.is_auto)

  if (remainder_mode.value === 'full_pallet_merge') {
    // 合板：同规格尾板合并，可少开托
    if (remRows.length === 0) { recalcSummary(); return }
    const groups = new Map<string, { rows: PackingRow[]; totalDrums: number; capacity: number }>()
    for (const r of remRows) {
      const pkg = packageTypes.value.find(p => p.name === r.packaging_name)
      if (!pkg) continue
      const capacity = r.remainder_pallet_spec.includes('1.0*1.0')
        ? ((pkg as any).pallet_qty_1x1 ?? 0)
        : ((pkg as any).pallet_qty_1_1x1_1 ?? 0)
      const key = `${r.remainder_pallet_spec}|${capacity}`
      if (!groups.has(key)) groups.set(key, { rows: [], totalDrums: 0, capacity })
      const g = groups.get(key)!
      g.rows.push(r)
      g.totalDrums += r.remainder
    }
    let totalNewPallets = 0
    for (const [, g] of groups) {
      if (g.capacity <= 0 || g.totalDrums <= 0) continue
      const boardsNeeded = Math.ceil(g.totalDrums / g.capacity)
      totalNewPallets += boardsNeeded
      // 从各行收回已含的尾板托，再在首行加上合并后的托数
      for (const r of g.rows) {
        const full = Math.floor(r.drums / (r.drums_per_pallet || 1))
        r.pallets = full
        r.remainder = 0
        r.is_auto = false
        recalcRow(r)
      }
      const first = g.rows[0]
      first.pallets += boardsNeeded
      recalcRow(first)
    }
    mergePalletCount.value = 0 // 已写入行 pallets
  } else if (remainder_mode.value === 'full_pallet_independent') {
    // 独立：托数已含尾板，仅清展示
    for (const r of remRows) {
      r.remainder = 0
      r.is_auto = false
      recalcRow(r)
    }
  } else {
    // 无托盘：托数清零
    for (const r of remRows) {
      r.pallets = 0
      r.remainder = 0
      r.is_auto = false
      recalcRow(r)
    }
  }

  recalcSummary()
}

function recalcSummary() {
  const s = { total_drums: 0, total_pallets: 0, total_cbm: 0, total_weight_kg: 0, fits_20gp: true, fits_40gp: true }
  for (const r of rows.value) {
    s.total_drums += r.drums || 0
    s.total_pallets += r.pallets || 0
    s.total_cbm += r.total_cbm || 0
    s.total_weight_kg += r.total_weight_kg || 0
    if (!r.fits_20gp) s.fits_20gp = false
    if (!r.fits_40gp) s.fits_40gp = false
  }
  summary.value = s
}

function clearRows() {
  rows.value = []
  summary.value = { total_drums: 0, total_pallets: 0, total_cbm: 0, total_weight_kg: 0, fits_20gp: false, fits_40gp: false }
}

function getSummary() {
  return { ...summary.value, container_type: containerType.value }
}

function getRows() {
  return rows.value.map(r => ({
    internal_code: r.internal_code || r.product_name,
    product_name: r.product_name,
    packaging_name: r.packaging_name,
    pallet_spec: r.pallet_spec,
    drums: r.drums,
    pallets: r.pallets,
    drums_per_pallet: r.drums_per_pallet,
    net_weight_kg: r.quantity_kg,
    gross_weight_kg: r.total_weight_kg,
    volume_cbm: r.total_cbm,
    fits_20gp: containerType.value === 'none' ? '不装柜' : containerType.value.toUpperCase(),
    actual_fill_kg: r.actual_fill_kg,
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
.toolbar-label { font-size: 13px; color: #606266; white-space: nowrap; }
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
.remainder-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.remainder-row-item { display: flex; align-items: center; gap: 10px; }
.remainder-name { font-size: 13px; color: #e6a23c; min-width: 160px; }
.remainder-item { font-size: 13px; color: #e6a23c; }
.remainder-total { font-size: 13px; font-weight: 600; color: #f56c6c; }
.remainder-mode { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.mode-label { font-size: 13px; color: #606266; }
.remainder-contribution { font-size: 13px; color: #409eff; margin-bottom: 8px; }
.calc-hint { font-size: 11px; color: #909399; }
</style>
