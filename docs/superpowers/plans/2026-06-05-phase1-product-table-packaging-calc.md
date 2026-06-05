# Phase1 产品明细 & 包装计算改进 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Phase1 工作流页面完成两项改动：(1) 产品明细表增加「内部编码」列；(2) 包装计算改为多行输入+混装模式+移除方案对比

**Architecture:** 前端 Vue 3 单文件组件修改，不涉及后端接口变更。PackagingCalculator 组件重写为多行输入模式，Phase1Workflow 调整产品明细列和联动逻辑。

**Tech Stack:** Vue 3 + Element Plus + TypeScript

---

## 文件变更范围

| 文件 | 变更内容 |
|------|---------|
| `frontend/src/views/phase1/Phase1Workflow.vue` | 产品明细表增加内编列；包装计算卡片替换为多行计算表格 |
| `frontend/src/components/phase1/PackagingCalculator.vue` | 移除方案对比；下拉加宽；多行输入+混装逻辑 |
| `frontend/src/api/phase1.ts` | 保存接口的 packaging_result 类型扩展（支持多产品汇总） |

---

## Task 1: 产品明细表增加「内部编码」列

**Files:**
- Modify: `frontend/src/views/phase1/Phase1Workflow.vue:75-109`

- [ ] **Step 1: 在 el-table 中增加 internal_code 列**

在第 76 行 `product_cn` 列之前插入新列：

```html
<el-table :data="orderForm.items" border stripe size="small" max-height="350">
  <el-table-column prop="internal_code" label="内部编码" width="100" />
  <el-table-column prop="product_cn" label="产品中文名" min-width="120" />
  ...
```

确认 `orderForm.items` 中每项已包含 `internal_code` 字段（`handleOrderParse` 中已映射，无需修改后端）。

---

## Task 2: PackagingCalculator 组件 — 移除方案对比 + 下拉加宽

**Files:**
- Modify: `frontend/src/components/phase1/PackagingCalculator.vue`

### Task 2A: 移除「可用方案对比」区块

- [ ] **Step 1: 删除 allSchemes ref 和相关逻辑**

删除第 139 行 `const allSchemes = ref<any[]>([])` 和第 99-118 行「全方案比较」模板区块。

- [ ] **Step 2: 删除 onPackageChange 中重置 allSchemes 的逻辑**

第 155-157 行 `onPackageChange` 只需 `result.value = null`。

- [ ] **Step 3: 删除 runCalculate 中填充 allSchemes 的逻辑**

第 171 行 `allSchemes.value = schemes` 删除；第 174-179 行选方案逻辑保留。

### Task 2B: 下拉框加宽

- [ ] **Step 1: 给 el-select 添加 popper-class 样式加宽**

在 `el-select` 上添加 `popper-class="pkg-select-popper"`，并在 `<style>` 中添加：

```css
.pkg-select-popper {
  min-width: 320px !important;
}
```

- [ ] **Step 2: 确认包装种类选项显示完整尺寸信息**

第 13-21 行已使用 `<span class="pkg-opt">{{ p.name }}</span><span class="pkg-dims">{{ p.dims }}</span>` 格式，保持不变。

---

## Task 3: PackagingCalculator 组件 — 多行输入 + 混装逻辑

**Files:**
- Modify: `frontend/src/components/phase1/PackagingCalculator.vue`

### Task 3A: 数据模型改造

- [ ] **Step 1: 定义包装行接口**

在 `<script>` 顶部添加：

```typescript
interface PackingRow {
  id: string          // 唯一 id，用于 key
  product_name: string
  packaging_name: string
  pallet_spec: string
  quantity_kg: number
  drums: number
  pallets: number
  drums_per_pallet: number
  total_cbm: number
  total_weight_kg: number
  fits_20gp: boolean
  fits_40gp: boolean
  merge_to_prev: boolean  // 拼入上一卡板
}
```

- [ ] **Step 2: 替换 result 为 rows 数组**

```typescript
const rows = ref<PackingRow[]>([])
const summary = ref({ total_drums: 0, total_pallets: 0, total_cbm: 0, total_weight_kg: 0, fits_20gp: false, fits_40gp: false })
```

### Task 3B: 模板改造 — 多行输入表格

- [ ] **Step 1: 用 el-table 替换单个 calc-form**

删除第 3-66 行 `calc-form` 相关代码，替换为：

```html
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
        <el-select v-model="row.packaging_name" placeholder="选择包装" size="small" filterable popper-class="pkg-select-popper" @change="(val) => onRowPackageChange(row, val)">
          <el-option v-for="p in packageTypes" :key="p.name" :label="p.name" :value="p.name">
            <span class="pkg-opt">{{ p.name }}</span>
            <span class="pkg-dims">{{ p.dims }}</span>
          </el-option>
        </el-select>
      </template>
    </el-table-column>
    <el-table-column label="卡板规格" width="140">
      <template #default="{ row }">
        <el-select v-model="row.pallet_spec" placeholder="选择托盘" size="small" :disabled="!row.packaging_name">
          <el-option v-for="p in palletTypes" :key="p.name" :label="p.name" :value="p.name" />
        </el-select>
      </template>
    </el-table-column>
    <el-table-column label="数量(kg)" width="120">
      <template #default="{ row }">
        <el-input-number v-model="row.quantity_kg" size="small" :min="0" controls-position="right" />
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
```

### Task 3C: 行操作方法

- [ ] **Step 1: 实现 addRow 方法**

```typescript
function addRow(productName = '', quantityKg = 0) {
  rows.value.push({
    id: Date.now().toString(),
    product_name: productName,
    packaging_name: '',
    pallet_spec: '1.1*1.1m',
    quantity_kg: quantityKg,
    drums: 0,
    pallets: 0,
    drums_per_pallet: 0,
    total_cbm: 0,
    total_weight_kg: 0,
    fits_20gp: false,
    fits_40gp: false,
    merge_to_prev: false,
  })
}
```

- [ ] **Step 2: 实现 removeRow 方法**

```typescript
function removeRow(index: number) {
  rows.value.splice(index, 1)
  recalcSummary()
}
```

- [ ] **Step 3: 实现 onRowPackageChange 行计算触发**

```typescript
async function onRowPackageChange(row: PackingRow, packagingName: string) {
  if (!packagingName || row.quantity_kg <= 0) return
  try {
    const schemes = await packagingApi.calculateSchemes({
      packaging_name: packagingName,
      order_qty_kg: row.quantity_kg,
      use_pallet: !!row.pallet_spec,
    })
    const match = schemes.find(s => s.pallet_type === row.pallet_spec) || schemes[0]
    if (match) {
      row.drums = match.drums
      row.pallets = match.pallets
      row.drums_per_pallet = match.drums_per_pallet
      row.total_cbm = match.total_cbm
      row.total_weight_kg = match.total_weight_kg
      row.fits_20gp = match.fits_20gp
      row.fits_40gp = match.fits_40gp
    }
    recalcSummary()
  } catch (e) {
    console.error('行计算失败', e)
  }
}
```

- [ ] **Step 4: 实现 recalcSummary 汇总计算**

```typescript
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
```

### Task 3D: 暴露方法给父组件

- [ ] **Step 1: 更新 defineExpose**

```typescript
defineExpose({
  addRow,          // 供父组件添加行（如从订单带入产品）
  setQuantity,     // 保留，初始化某行数量
  selectPackage,   // 保留，设置某行包装种类
  getSummary,      // 新增，返回汇总数据
})
```

```typescript
function getSummary() {
  return summary.value
}
```

### Task 3E: 样式

- [ ] **Step 1: 添加样式**

```css
.calc-table-wrapper { padding: 4px 0; }
.calc-toolbar { margin-bottom: 8px; }
.calc-table { margin-bottom: 12px; }
.calc-summary { margin-top: 8px; }
.pkg-select-popper { min-width: 320px !important; }
```

---

## Task 4: Phase1Workflow 联动 — 带入订单产品到包装计算器

**Files:**
- Modify: `frontend/src/views/phase1/Phase1Workflow.vue:144-154`

- [ ] **Step 1: 在包装计算卡片模板中给 PackagingCalculator 传递产品列表**

在 `<PackagingCalculator ref="calcRef">` 上添加 `:products="orderForm.items"` prop：

```html
<PackagingCalculator
  ref="calcRef"
  :products="orderForm.items"
  @calculated="onPackagingCalculated"
/>
```

- [ ] **Step 2: 在 syncCalculatorFromOrder 中改为调用 addRow 批量添加产品行**

删除第 238-255 行 `syncCalculatorFromOrder` 逻辑，替换为：

```typescript
function syncCalculatorFromOrder() {
  if (!calcRef.value) return
  calcRef.value.clearRows()
  for (const item of orderForm.value.items) {
    // 自动推荐包装种类
    const specMap = { 25: '25kg正方罐（蓝色）', 30: '30kg蓝桶', 50: '50kg蓝桶(大口)', 60: '60kg蓝桶', 125: '125kg新款胶桶', 150: '150kg新款胶桶', 200: '200kg双环闭口桶', 1000: '1吨桶(IBC)' }
    const pkgName = specMap[item.spec_kg] || ''
    calcRef.value.addRow(item.product_cn || '', item.quantity_kg || 0)
  }
}
```

- [ ] **Step 3: 更新 onPackagingCalculated 处理汇总数据**

```typescript
function onPackagingCalculated(summary: any) {
  packagingResult.value = summary
}
```

- [ ] **Step 4: PackagingCalculator 新增 clearRows 方法（暴露）**

在 `PackagingCalculator.vue` 的 `defineExpose` 中添加 `clearRows`:

```typescript
function clearRows() {
  rows.value = []
  summary.value = { total_drums: 0, total_pallets: 0, total_cbm: 0, total_weight_kg: 0, fits_20gp: false, fits_40gp: false }
}
defineExpose({ addRow, clearRows, setQuantity, selectPackage, getSummary })
```

- [ ] **Step 5: 保存时传递包装汇总数据**

`handleConfirmSave` 中的 `packagingResult` 改为直接取 `calcRef.value?.getSummary()`：

```typescript
packagingResult.value = calcRef.value?.getSummary() || null
```

---

## Task 5: 移除包装计算区块的"可用方案对比"

确认 Task 2A 已覆盖此步骤。

---

## 自检清单

- [ ] 产品明细表有 internal_code 列，且只读显示
- [ ] 包装计算表格每行可独立选择产品和包装种类
- [ ] 下拉框宽度足够显示完整包装名称+尺寸
- [ ] 移除方案对比表格
- [ ] 汇总行显示总桶数、总托盘数、总体积、总毛重、20GP判断
- [ ] 从订单解析后自动带入产品到包装计算表格
- [ ] 保存时包装汇总数据正确传递