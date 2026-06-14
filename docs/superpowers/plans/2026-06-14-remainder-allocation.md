# 包装计算余数处理优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 当产品桶数除以每板桶数有余数时，主表只显示整板数（floor），底部散货区显示余数桶并提供三种装载计算模式，用户选择后把散货贡献加入汇总。

**Architecture:** 后端 `packaging_service.py` 新增 `full_pallets`（整板数）和 `remainder`（余数桶）字段；前端 `PackagingCalculator.vue` 主表显示整板数，底部用 `el-collapse` 内嵌散货区，提供三种计算模式单选组和"重新计算汇总"按钮。

**Tech Stack:** Vue 3 + Element Plus + FastAPI + SQLAlchemy

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `backend/app/services/packaging_service.py` | `ProductPackagingResult` 新增字段；新增余数计算函数 |
| `backend/app/api/v1/packaging.py` | `PackingScheme` 新增 `full_pallets` |
| `frontend/src/api/packaging.ts` | `PackingScheme` 接口新增 `full_pallets` |
| `frontend/src/components/phase1/PackagingCalculator.vue` | 主表整板数显示；底部散货区；remainder_mode 逻辑 |

---

## 界面布局

```
┌─────────────────────────────────────────────────────────┐
│ 主表格（包装计算器）                                     │
│ 产品 | 包装 | 卡板规格 | 数量 | 每板桶数 | 桶数 | 托盘数 | 体积 | 毛重
│  A   | 125kg桶 | 1.1*1.1 | 41kg | 8 | 40 | 5 | 0.640 | 660kg
│  B   | 125kg桶 | 1.1*1.1 | 20kg | 8 | 16 | 2 | 0.256 | 330kg
├─────────────────────────────────────────────────────────┤
│ ▼ 非整板货物统计（需确认装载方式）  [默认展开]            │
│                                                         │
│  A-余数:1桶  |  B-余数:4桶  |  合计:5桶                  │
│                                                         │
│  散货装载计算模式：                                      │
│  ( ) 按整板计算    — 余数凑整板，算一整卡板体积+重量      │
│  (•) 按实际堆叠    — 只加余数桶自身体积/重量，不加卡板自身│
│  ( ) 散货混装      — 只算净体积，不加皮重和卡板体积       │
│                                                         │
│  散货贡献：+0.048 CBM | +105 kg                         │
│                              [重新计算汇总]             │
└─────────────────────────────────────────────────────────┘
```

---

## 三种计算模式

| 模式 | 散货体积 | 散货重量 | 适用场景 |
|------|---------|---------|---------|
| 按整板计算 | `+1 整卡板体积` | `+1 整卡板重量+余数桶皮重` | 余数单独打一板 |
| 按实际堆叠（默认） | `+余数桶体积` | `+余数桶皮重` | 并入其他板/塞缝隙 |
| 散货混装 | `+余数桶净体积` | `+余数桶净重` | 散装不打托 |

---

## Task 1: 后端 — packaging_service.py 新增 full_pallets 和 remainder

**Files:**
- Modify: `backend/app/services/packaging_service.py:71-89`

- [ ] **Step 1: `ProductPackagingResult` 新增字段**

```python
@dataclass
class ProductPackagingResult:
    """单个产品的包装计算结果"""
    product_name: str
    packaging_name: str
    specification_kg: float

    drums: int                  # 桶数/袋数
    drums_per_pallet: int       # 每板桶数
    pallets: int                # 整板数 = drums // drums_per_pallet
    pallet_spec: str            # 使用的卡板规格
    full_pallets: int          # 整板数（与 pallets 相同，兼容用）
    remainder: int             # 余数桶数 = drums % drums_per_pallet

    net_weight_kg: float         # 产品净重
    drum_tare_kg: float         # 桶身皮重
    pallet_tare_kg: float       # 卡板皮重
    gross_weight_kg: float     # 总毛重
    drum_cbm: float             # 桶身体积
    pallet_cbm: float           # 卡板体积
    total_volume_cbm: float    # 总体积
```

- [ ] **Step 2: `calculate_single_product()` 修改计算逻辑**

在 `calculate_single_product()` 函数中（大约第342行），将：
```python
pallets = math.ceil(drums / drums_per_pallet)
```
改为：
```python
full_pallets = drums // drums_per_pallet
remainder = drums % drums_per_pallet
pallets = full_pallets  # 兼容旧字段，存整板数
```

在返回的 `ProductPackagingResult` 中新增：
```python
return ProductPackagingResult(
    ...
    full_pallets=full_pallets,
    remainder=remainder,
    ...
)
```

- [ ] **Step 3: 新增 `calculate_remainder_contribution()` 函数**

在文件末尾（`packaging_service.py`）新增：

```python
def calculate_remainder_contribution(
    remainder_drums: int,
    packaging_name: str,
    pallet_spec: str,
    mode: str,  # "full_pallet" | "actual_stacked" | "loose"
) -> Tuple[float, float]:
    """
    计算余数桶对总体积/总重量的贡献。

    mode:
      - full_pallet:       余数凑整板，算一整卡板体积+重量
      - actual_stacked:    只加余数桶自身（体积+皮重），不加卡板自身
      - loose:             只加余数桶净体积，不加任何皮重
    """
    pkg = find_package(packaging_name)
    if not pkg or remainder_drums <= 0:
        return 0.0, 0.0

    pallet = find_pallet(pallet_spec) if pallet_spec else None

    if mode == "full_pallet":
        extra_volume = pallet.cbm if pallet else 0.0
        extra_weight = (
            (remainder_drums * pkg.tare_kg) +
            (pallet.weight_kg if pallet else 0.0)
        )
    elif mode == "actual_stacked":
        extra_volume = remainder_drums * pkg.cbm
        extra_weight = remainder_drums * pkg.tare_kg
    else:  # loose
        extra_volume = remainder_drums * pkg.cbm
        extra_weight = remainder_drums * pkg.net_kg

    return round(extra_volume, 4), round(extra_weight, 1)
```

- [ ] **Step 4: `PackingResult` 新增 full_pallets 字段**

在 `PackingResult` dataclass 中新增：
```python
full_pallets: int = 0
```

同时在 `calculate()` 函数中（大约第237行），将 `pallets = math.ceil(drums / drums_per_pallet)` 改为：
```python
full_pallets = drums // drums_per_pallet
remainder_val = drums % drums_per_pallet
pallets = full_pallets
```

在返回 `PackingResult` 时填充：
```python
return PackingResult(
    ...
    full_pallets=full_pallets,
    ...
)
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/packaging_service.py
git commit -m "feat(packaging): add full_pallets and remainder to ProductPackagingResult"
```

---

## Task 2: 后端 — packaging.py API 新增 full_pallets

**Files:**
- Modify: `backend/app/api/v1/packaging.py:29-39` 和 `114-133`

- [ ] **Step 1: `PackingScheme` 新增 full_pallets 字段**

```python
class PackingScheme(BaseModel):
    drums: int
    pallets: int
    drums_per_pallet: int
    pallet_type: Optional[str]
    total_cbm: float
    total_weight_kg: float
    fits_20gp: bool
    fits_40gp: bool
    recommended: str
    remainder: int = 0  # 余数桶数（已有）
    full_pallets: int = 0  # 整板数（新增）
```

- [ ] **Step 2: `calculate_all_packaging_schemes` 返回 full_pallets**

在序列化 schemes 时（大约第119-133行），在每个 dict 中加入：
```python
{
    ...
    "full_pallets": s.full_pallets if hasattr(s, 'full_pallets') else (s.drums // s.drums_per_pallet if s.drums_per_pallet else 0),
}
```

- [ ] **Step 3: `calculate_packaging` 单个方案返回 full_pallets**

在 `calculate_packaging` 函数中（两个 return 分支），加入：
```python
full_pallets=best.drums // best.drums_per_pallet if best.drums_per_pallet else 0,
```
和
```python
full_pallets=0,
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/api/v1/packaging.py
git commit -m "feat(packaging): add full_pallets to PackingScheme API response"
```

---

## Task 3: 前端 — packaging.ts 接口新增 full_pallets

**Files:**
- Modify: `frontend/src/api/packaging.ts:24-34`

- [ ] **Step 1: `PackingScheme` 接口新增 full_pallets**

```typescript
export interface PackingScheme {
  drums: number
  pallets: number
  drums_per_pallet: number
  pallet_type: string | null
  total_cbm: number
  total_weight_kg: number
  fits_20gp: boolean
  fits_40gp: boolean
  recommended: string
  remainder: number  // 余数桶数（已有）
  full_pallets: number  // 整板数（新增）
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/api/packaging.ts
git commit -m "feat(frontend): add full_pallets to PackingScheme interface"
```

---

## Task 4: 前端 — PackagingCalculator.vue 主表显示整板数 + 底部散货区

**Files:**
- Modify: `frontend/src/components/phase1/PackagingCalculator.vue`

- [ ] **Step 1: `PackingRow` 接口新增 full_pallets 和 remainder**

在 `PackingRow` 接口中添加：
```ts
full_pallets: number   // 整板数
remainder: number     // 余数桶数
```

- [ ] **Step 2: 新增状态变量**

在 `<script setup>` 中添加：
```ts
const remainder_mode = ref<'full_pallet' | 'actual_stacked' | 'loose'>('actual_stacked')
const showRemainderSection = ref(true)
```

- [ ] **Step 3: 修改 `addRow()` 初始值**

在 `addRow()` 函数中新增行的初始化，添加：
```ts
full_pallets: 0,
remainder: 0,
```

- [ ] **Step 4: 修改 `onRowPackageChange()` 从 API 提取 full_pallets**

在 API 响应赋值处（大约第254行附近），添加：
```ts
row.full_pallets = match.full_pallets ?? (match.drums // match.drums_per_pallet)
row.remainder = match.remainder ?? (match.drums % match.drums_per_pallet)
```

同时在主表模板列中将"托盘数"显示 `row.pallets` 改为 `row.full_pallets`。

- [ ] **Step 5: 修改 `onRowCapacityChange()` 手动计算 full_pallets**

将手动计算逻辑从 `ceil` 改为整数除法：
```ts
const drums = Math.ceil(row.quantity_kg / pkg.net_kg)
row.drums = drums
row.full_pallets = Math.floor(drums / row.drums_per_pallet)
row.remainder = drums % row.drums_per_pallet
row.pallets = row.full_pallets
```

- [ ] **Step 6: 新增 `calcRemainderContribution()` 函数**

```ts
function calcRemainderContribution() {
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
```

- [ ] **Step 7: 修改 `recalcSummary()` 包含散货贡献**

```ts
function recalcSummary() {
  const { extraCbm, extraWeight } = calcRemainderContribution()
  const s = {
    total_drums: 0, total_pallets: 0, total_cbm: 0, total_weight_kg: 0,
    fits_20gp: true, fits_40gp: true, pending_drums: 0
  }
  for (const r of rows.value) {
    s.total_drums += r.drums || 0
    s.total_pallets += r.full_pallets || 0
    s.total_cbm += r.total_cbm || 0
    s.total_weight_kg += r.total_weight_kg || 0
    if (!r.fits_20gp) s.fits_20gp = false
    if (!r.fits_40gp) s.fits_40gp = false
  }
  s.total_pallets += remainder_mode.value === 'full_pallet'
    ? rows.value.filter(r => r.remainder > 0).length
    : 0
  s.total_cbm += extraCbm
  s.total_weight_kg += extraWeight
  summary.value = s
}
```

- [ ] **Step 8: 模板新增底部散货区**

在 `</el-descriptions>` 之后、`<RemainderAllocationDialog>` 之前添加：

```vue
<!-- 散货区 -->
<el-collapse v-model="showRemainderSection" class="remainder-section">
  <el-collapse-item title="非整板货物统计（需确认装载方式）" name="remainder">
    <div v-if="remainderRows.length === 0" class="remainder-empty">无余数桶</div>
    <template v-else>
      <div class="remainder-list">
        <span v-for="r in remainderRows" :key="r.id" class="remainder-item">
          {{ r.product_name }}-余数: {{ r.remainder }}桶
        </span>
        <span class="remainder-total">合计: {{ totalRemainderDrums }}桶</span>
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
    </template>
  </el-collapse-item>
</el-collapse>
```

对应的 computed 和 data 追加：
```ts
const remainderRows = computed(() => rows.value.filter(r => r.remainder > 0))
const totalRemainderDrums = computed(() => remainderRows.value.reduce((s, r) => s + r.remainder, 0))
const { extraCbm: remainderExtraCbm, extraWeight: remainderExtraWeight } = calcRemainderContribution()
```

- [ ] **Step 9: 新增散货区样式**

```css
.remainder-section { margin-top: 8px; }
.remainder-empty { color: #909399; font-size: 13px; padding: 8px 0; }
.remainder-list { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.remainder-item { font-size: 13px; color: #e6a23c; }
.remainder-total { font-size: 13px; font-weight: 600; color: #f56c6c; }
.remainder-mode { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.mode-label { font-size: 13px; color: #606266; }
.remainder-contribution { font-size: 13px; color: #409eff; margin-bottom: 8px; }
```

- [ ] **Step 10: 删除 `RemainderAllocationDialog` 相关引用**

移除之前添加的 `RemainderAllocationDialog` 导入和 `showRemainderDialog` 状态，以及模板中的 `<RemainderAllocationDialog>` 组件。

- [ ] **Step 11: 提交**

```bash
git add frontend/src/components/phase1/PackagingCalculator.vue
git rm frontend/src/components/phase1/RemainderAllocationDialog.vue
git commit -m "refactor(PackagingCalculator): replace dialog with bottom remainder section"
```

---

## 验证方式

1. 启动后端：`cd backend && uvicorn app.main:app --reload --port 8000`
2. 启动前端：`cd frontend && npm run dev`，打开 http://localhost:5173/phase1
3. 打开包装计算器，添加一行：选择"125kg新款胶桶"，输入数量 41kg
4. 验证主表托盘数列显示 **5**（41//8=5，整板数），不再显示 ceil 值 6
5. 展开底部散货区，验证显示 "A-余数: 1桶"
6. 选择"按整板计算"，点击"重新计算汇总"，验证托盘数变为 **6**，总重量包含新卡板自身重量
7. 选择"按实际堆叠"，点击"重新计算汇总"，验证托盘数保持 5，总重量只加余数桶皮重
8. 选择"散货混装"，点击"重新计算汇总"，验证总重量只加净重（不加皮重）

---

**Plan complete and saved to `docs/superpowers/plans/2026-06-14-remainder-allocation.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**