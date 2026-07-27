# 包装计算加入"不打卡板"选项 — 设计文档

## 概述

当前包装计算中，对于可打卡板的产品（`is_palletizable: true`），用户必须选择卡板规格（1.0*1.0m 或 1.1*1.1m）。但实际业务中，有些货物虽然可以打卡板，具体的订单可能不需要打卡板。为此，在卡板规格下拉框中增加"不打卡板"选项。

## 改动范围

采用**方案 A**：空字符串 `""` 作为"不打卡板"的 sentinel 值，后端将 `""` 和 `None` 统一视为不打卡板。

### 涉及的模块

| 层 | 文件 | 改动 |
|----|------|------|
| 前端 | `frontend/src/components/phase1/PackagingCalculator.vue` | 下拉框增加"不打卡板"选项，关联 UI 行为调整 |
| 后端 | `backend/app/services/packaging_service.py` | `calculate_single_product()` 增加空值时直接不打卡板计算 |
| 后端 | `backend/app/api/v1/packaging.py` | `OrderProductItem.pallet_spec` 改为 Optional |
| 后端 | `backend/app/schemas/order_pi_record.py` | `ProductPackagingItem.pallet_spec` 改为 Optional |
| 后端 | `backend/app/services/save_service.py` | 已支持可选值，无需改动 |

### 不受影响的部分

- 数据库架构 — `pallet_spec TEXT` 列已支持 NULL
- 订单级别汇总 API `POST /api/v1/packaging/calculate-order` — 已通过 `calculate_single_product()` 自然支持

## 详细设计

### 前端 PackagingCalculator.vue

**1. 卡板规格下拉框改动**

在现有下拉框选项列表顶部添加固定选项：
```
{ label: "不打卡板", value: "" }
```
此选项**始终可用**，不受 `isPalletizable()` 影响。

**2. 选中"不打卡板"时的 UI 行为**

- "每卡板桶数"列：显示 `—`（文字居中，灰色），`el-input-number` 不渲染
- "板数"列：显示 `—`，`el-input-number` 不渲染
- 选中时自动触发 `onRowPackageChange()` → 调用 API 的 `use_pallet: False`

判断条件：`row.pallet_spec === ""`

**3. `onRowPackageChange()` 调整**

当 `pallet_spec === ""` 时：
```
usePallet = false
```
此时后端 API 返回不打卡板计算结果（无卡板体积/重量）。

**4. `getRows()` 输出**

不变，`pallet_spec` 为空字符串（`""`）时，保存服务自然处理。

**5. `isPalletizable()` 辅助函数调整**

当前逻辑：当 `packagingName` 为空或找不到时返回 `true`。
新增逻辑：即使 `is_palletizable` 为 `true`，如果用户选中了"不打卡板"，仍然隐藏相关列。

由 `row.pallet_spec === ""` 判定，不依赖 `isPalletizable()`。

### 后端 packaging_service.py

**`calculate_single_product()` 函数**

在函数顶部增加早返回分支：

```python
def calculate_single_product(..., pallet_spec: str = "1.1*1.1m"):
    pkg = find_package(packaging_name)
    if not pkg:
        raise ValueError(...)
    
    fill_kg = actual_fill_kg if actual_fill_kg and actual_fill_kg > 0 else specification_kg
    drums = math.ceil(quantity_kg / fill_kg)
    
    # 不打卡板模式
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
    
    # 原打卡板逻辑...
```

**`calculate_order_packaging()` 函数**

在按卡板规格分组时，跳过 `pallet_spec=""` 的产品：

```python
for prod_result in product_details:
    if prod_result.pallets > 0 and prod_result.pallet_spec:
        spec = prod_result.pallet_spec
        ...
```

**`ProductPackagingResult.pallet_spec` 类型**

从 `str` 改为保持 `str`（因为空字符串 `""` 仍为 `str` 类型）。无需修改。

### 后端 packaging.py API

```python
class OrderProductItem(BaseModel):
    ...
    pallet_spec: Optional[str] = None  # None / "" = 不打卡板
```

### 数据流示例

用户操作顺序：
1. 选择包装种类 "125kg新款胶桶"
2. 卡板规格选择 "不打卡板"
3. 输入数量 500kg
4. → 前端设置 `use_pallet: false`
5. → 后端返回：桶数=4, 板数=0, 体积=0.84CBM, 毛重=524kg
6. → 前端展示：板数列显示 `—`
