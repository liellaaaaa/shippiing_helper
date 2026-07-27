# 包装计算加入"不打卡板"选项 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在包装计算中为所有产品（包括可打卡板的产品）增加"不打卡板"选项。

**Architecture:** 使用空字符串 `""` 作为 sentinel 值表示"不打卡板"，前端下拉框增加选项，后端已有 `drums_per_pallet=0` 分支可复用，只需增加明确的早返回逻辑。

**Tech Stack:** Vue 3 + TypeScript (前端), FastAPI + Python (后端)

---

### Task 1: 后端 `packaging_service.py` — 增加不打卡板早返回逻辑

**Files:**
- Modify: `backend/app/services/packaging_service.py` (lines 312-389)

- [ ] **Step 1: 修改 `calculate_single_product()` 增加不打卡板分支**

在 `drums = math.ceil(quantity_kg / fill_kg)` 之后、现有"确定每托盘桶数"逻辑之前，插入不打卡板的早返回：

```python
    # 不打卡板模式：当 pallet_spec 为空/None 时，直接计算桶数体积毛重，无卡板贡献
    if not pallet_spec:
        drum_tare = drums * pkg.tare_kg
        drum_cbm = drums * pkg.cbm
        total_volume = drum_cbm
        gross_weight = drums * pkg.gross_kg

        return ProductPackagingResult(
            product_name=packaging_name,
            packaging_name=packaging_name,
            specification_kg=specification_kg,
            drums=drums,
            drums_per_pallet=0,
            pallets=0,
            pallet_spec="",
            full_pallets=0,
            remainder=0,
            net_weight_kg=quantity_kg,
            drum_tare_kg=round(drum_tare, 1),
            pallet_tare_kg=0,
            gross_weight_kg=round(gross_weight, 1),
            drum_cbm=round(drum_cbm, 4),
            pallet_cbm=0,
            total_volume_cbm=round(total_volume, 4),
        )
```

- [ ] **Step 2: 修改 `calculate_order_packaging()` — 跳过不打卡板产品加入卡板分组**

找到按卡板规格分组的 for 循环（约第 440 行），修改条件：

```python
    for prod_result in product_details:
        if prod_result.pallets > 0 and prod_result.pallet_spec:
            spec = prod_result.pallet_spec
            if spec not in pallet_groups:
                pallet_groups[spec] = {"count": 0, "drums": 0, "volume": 0.0, "weight": 0.0}
            pallet_groups[spec]["count"] += prod_result.pallets
            pallet_groups[spec]["drums"] += prod_result.drums
            pallet_groups[spec]["volume"] += prod_result.pallet_cbm
            pallet = find_pallet(spec)
            pallet_groups[spec]["weight"] += prod_result.pallets * (pallet.weight_kg if pallet else 0)
```

- [ ] **Step 3: 验证改动**

```bash
cd backend && python -c "
from app.services.packaging_service import calculate_single_product
# 不打卡板测试
r = calculate_single_product('125kg新款胶桶', 500, 125, '胶桶', '')
assert r.pallets == 0, 'expected no pallets'
assert r.drums_per_pallet == 0
assert r.pallet_spec == ''
assert r.pallet_cbm == 0
assert r.pallet_tare_kg == 0
assert r.total_volume_cbm > 0  # 只有桶体体积
print('NO_PALLET OK:', r)

# 打卡板测试（确保原有逻辑不受影响）
r2 = calculate_single_product('125kg新款胶桶', 500, 125, '胶桶', '1.1*1.1m')
assert r2.pallets > 0
assert r2.pallet_spec == '1.1*1.1m'
print('WITH_PALLET OK:', r2)
"
```

预期输出：两个 OK 打印，无异常。

---

### Task 2: 后端 API 类型调整

**Files:**
- Modify: `backend/app/api/v1/packaging.py`

- [ ] **Step 1: 修改 `OrderProductItem` 模型的 `pallet_spec` 类型**

```python
class OrderProductItem(BaseModel):
    ...
    pallet_spec: Optional[str] = None  # None 或 "" = 不打卡板
```

同文件下的输出序列化（约第 195-211 行）已使用 `p.pallet_spec` 透传，无需额外处理。`None` 会被 Pydantic 序列化为 `null`。

- [ ] **Step 2: 验证 API**

```bash
cd backend && python -c "
from app.api.v1.packaging import OrderProductItem
# None 和空字符串都应接受
item1 = OrderProductItem(product_name='test', packaging_name='125kg新款胶桶', quantity_kg=500, specification_kg=125)
assert item1.pallet_spec is None, 'default should be None'
item2 = OrderProductItem(product_name='test', packaging_name='125kg新款胶桶', quantity_kg=500, specification_kg=125, pallet_spec='')
assert item2.pallet_spec == '', 'empty string allowed'
print('API schema OK')
"
```

---

### Task 3: 后端 Schema 类型调整

**Files:**
- Modify: `backend/app/schemas/order_pi_record.py`

- [ ] **Step 1: 修改 `PackagingResult` 中 pallet_spec 默认值**

```python
class PackagingResult(BaseModel):
    ...
    pallet_spec: Optional[str] = None  # 已为 Optional，无需改动
```

确认该文件第 8 行已是 `pallet_spec: Optional[str] = None`。

- [ ] **Step 2: 修改 `ProductPackagingItem` 的 `pallet_spec` 类型**

第 132 行：
```python
class ProductPackagingItem(BaseModel):
    ...
    pallet_spec: Optional[str] = None  # 从 str 改为 Optional
```

- [ ] **Step 3: 验证 schema**

```bash
cd backend && python -c "
from app.schemas.order_pi_record import ProductPackagingItem
item = ProductPackagingItem(
    product_name='test', packaging_name='pkg', specification_kg=125,
    drums=4, drums_per_pallet=0, pallets=0, pallet_spec=None,
    net_weight_kg=500, gross_weight_kg=524, volume_cbm=0.84
)
assert item.pallet_spec is None
print('Schema OK')
"
```

---

### Task 4: 前端 `PackagingCalculator.vue` — 增加"不打卡板" UI 和交互

**Files:**
- Modify: `frontend/src/components/phase1/PackagingCalculator.vue`

- [ ] **Step 1: 在卡板规格下拉框中增加"不打卡板"选项**

找到卡板规格列的 `<el-select>` 代码（约第 35-43 行），在 `v-for` 选项之前增加固定选项：

```vue
<el-select v-if="isPalletizable(row.packaging_name) || true" v-model="row.pallet_spec" placeholder="选择托盘" size="small" :disabled="!row.packaging_name" @change="() => onRowPackageChange(row, row.packaging_name)">
  <!-- 不打卡板选项，始终可用 -->
  <el-option label="不打卡板" value="" />
  <el-option
    v-for="p in palletTypes"
    :key="p.name"
    :label="p.name"
    :value="p.name"
    :disabled="isPalletUnsupported(row.packaging_name, p.name)"
  />
</el-select>
```

- [ ] **Step 2: 修改"每卡板桶数"列 — 不打卡板时显示 `—`**

找到该列模板（约第 65-79 行），增加空值判断：

```vue
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
```

- [ ] **Step 3: 修改"板数"列 — 不打卡板时显示 `—`**

找到该列模板（约第 82-109 行），修改外层条件：

```vue
<el-table-column label="板数" width="130" align="center">
  <template #default="{ row }">
    <template v-if="isPalletizable(row.packaging_name) && row.pallet_spec !== ''">
      <!-- 现有板数编辑内容保持不变 -->
      ...
    </template>
    <span v-else style="color:#999;font-size:12px">—</span>
  </template>
</el-table-column>
```

- [ ] **Step 4: 修改 `onRowPackageChange()` — 不打卡板时调用 `use_pallet: False`**

找到 `usePallet` 变量赋值处（约第 399 行），修改为：

```typescript
// 不打卡板时强制不打卡板计算
const usePallet = isPalletizable(packagingName) && !!row.pallet_spec
if (!row.pallet_spec) {
  row.pallet_spec = ''
}
```

后端 `calculate` API 已支持 `use_pallet: false`，会返回无卡板结果。

- [ ] **Step 5: 验证前端编译**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

预期输出：无类型错误。

---

### Task 5: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 启动前端**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: 手动测试场景**

1. 打开包装计算页面
2. 添加产品，选择"125kg新款胶桶"
3. 卡板规格下拉框 → 可见"不打卡板"选项
4. 选择"不打卡板"
5. → "每卡板桶数"和"板数"列显示 `—`
6. → 汇总区：总体积 = 桶数 × 桶CBM，总毛重 = 桶数 × 桶毛重
7. 切回"1.1*1.1m" → 恢复正常卡板计算
8. 选择"1吨桶(IBC)"（`is_palletizable: false`）→ 仍显示"不打卡板"且可选
