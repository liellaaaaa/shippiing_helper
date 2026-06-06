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
        <el-table-column label="托盘数" width="70" align="center">
          <template #default="{ row }"><span>{{ row.pallets || '-' }}</span></template>
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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
  pallets: number
  drums_per_pallet: number
  drums_per_pallet_auto: number  // 自动填的标准值，供比较用
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

async function onRowCapacityChange(row: PackingRow) {
  // 用户手动修改了每卡板桶数，按实际值重新计算
  if (!row.packaging_name || row.quantity_kg <= 0 || row.drums_per_pallet <= 0) return
  const pkg = packageTypes.value.find(p => p.name === row.packaging_name)
  if (!pkg) return

  const drums = Math.ceil(row.quantity_kg / pkg.net_kg)
  row.drums = drums
  const pallets = Math.ceil(drums / row.drums_per_pallet)
  row.pallets = pallets
  row.total_cbm = drums * pkg.cbm
  row.total_weight_kg = drums * pkg.gross_kg + pallets * 20
  row.fits_20gp = row.total_cbm <= 28 && row.total_weight_kg <= 21000
  row.fits_40gp = row.total_cbm <= 67 && row.total_weight_kg <= 27000
  recalcSummary()
}

async function onRowPackageChange(row: PackingRow, packagingName: string) {
  if (!packagingName || row.quantity_kg <= 0) {
    row.drums = 0; row.pallets = 0; row.drums_per_pallet = 0
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
      row.pallets = match.pallets
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
.calc-table-wrapper { padding: 4px 0; }
.calc-toolbar { margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.calc-table { margin-bottom: 12px; }
.calc-summary { margin-top: 8px; }
.pkg-select-popper { min-width: 320px !important; }
.pkg-opt { font-weight: 500; }
.pkg-dims { font-size: 12px; color: #909399; margin-left: 8px; }
.drums-per-pallet-input { width: 80px; }
</style>
