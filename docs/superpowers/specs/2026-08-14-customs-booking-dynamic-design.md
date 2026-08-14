# 设计文档：报关资料动态扩展 & 订舱单同名合并

> 日期：2026-08-14
> 状态：已批准

---

## 1. 背景与需求

### 1.1 问题描述

1. **报关资料行数限制**：当前发票和箱单Sheet固定16行容量，当产品数量超过16个（如38个产品）时无法容纳
2. **订舱单同名显示**：当订单中有多个同名产品（如2个"防染剂"，不同海关编码/内编），订舱单会重复显示相同货名

### 1.2 需求目标

1. 发票和箱单Sheet支持动态扩展行数，参考报关单Sheet的现有实现
2. 订舱单按产品中文名（`product_cn`）去重合并，同名产品只显示一行

---

## 2. 现状分析

### 2.1 报关资料工作簿结构

| Sheet | 当前状态 | 预建容量 | 动态扩展 |
|-------|---------|---------|---------|
| 报关单 | ✅ 已实现 | 6块（每块3行） | 支持，`_extend_customs_sheet` |
| 发票 | ❌ 固定 | 16行（行8-23） | 不支持 |
| 箱单 | ❌ 固定 | 16行（行10-25） | 不支持 |
| 合同 | ✅ 公式引用 | N/A | 自动跟随发票 |
| 委托书 | ✅ 占位符 | N/A | 去重拼接 |

### 2.2 订舱单现状

- 模板占位符：`{{DESC1}}` ~ `{{DESC6}}`，最多6个产品
- 当前逻辑：每个产品各自占一行，不做去重
- 毛重/体积：汇总数值，不分行

---

## 3. 设计方案

### 3.1 发票Sheet动态扩展

**扩展逻辑**（参考 `_extend_customs_sheet`）：

```
预建容量：16行（行8-23）
扩展触发：N > 16
样式源：最后一行产品行（行23）
扩展方式：从行24起逐行插入，复制样式/行高/合并单元格
```

**特殊处理**：
- 产品1-4在行8-11
- 产品5起跳过预留行12/13，从行14开始
- 扩展时需保持与合同页公式引用的对齐

**关键代码位置**：
- 新增方法：`_extend_invoice_sheet(ws, n_items)`
- 调用位置：`generate_customs()` 中填充发票Sheet前

### 3.2 箱单Sheet动态扩展

**扩展逻辑**：

```
预建容量：16行（行10-25）
扩展触发：N > 16
样式源：最后一行产品行（行25）
扩展方式：从行26起逐行插入，复制样式/行高/合并单元格
```

**数据来源**：
- 部分通过OFFSET公式从报关单Sheet的T/U/V辅助列引用
- 部分直接填充（如包装类型、件数）

**关键代码位置**：
- 新增方法：`_extend_packing_sheet(ws, n_items)`
- 调用位置：`generate_customs()` 中填充箱单Sheet前

### 3.3 订舱单同名合并

**合并规则**：
- 按 `product_cn`（产品中文名）去重
- 保持原始顺序（使用 `dict.fromkeys()` 去重）
- 去重后的货名列表填充到 DESC1-DESC6

**数据流**：

```
原始数据：["防染剂", "防染剂", "柔软剂", "分散剂"]
     ↓ 去重
去重结果：["防染剂", "柔软剂", "分散剂"]
     ↓ 填充
DESC1=防染剂, DESC2=柔软剂, DESC3=分散剂
```

**关键代码位置**：
- 修改文件：`backend/app/api/v1/documents.py`
- 修改函数：`generate_booking()` 中构建 `customs_names` 的逻辑

---

## 4. 实现细节

### 4.1 `_extend_invoice_sheet` 方法

```python
def _extend_invoice_sheet(self, ws, n_items: int):
    """动态扩展发票Sheet行数"""
    prebuilt = 16  # 预建容量
    if n_items <= prebuilt:
        return
    
    # 样式源：最后一行产品行（行23）
    source_row = 23
    # 起始插入行：行24
    start_row = 24
    
    # 计算需要插入的行数
    rows_to_insert = n_items - prebuilt
    
    # 插入空行
    ws.insert_rows(start_row, rows_to_insert)
    
    # 复制样式和合并单元格
    for i in range(rows_to_insert):
        target_row = start_row + i
        # 复制单元格样式（A-J列）
        for col in range(1, 11):
            source_cell = ws.cell(row=source_row, column=col)
            target_cell = ws.cell(row=target_row, column=col)
            self._copy_cell_style(source_cell, target_cell)
        # 复制行高
        ws.row_dimensions[target_row].height = ws.row_dimensions[source_row].height
    
    # 更新打印区域
    last_row = 20 + n_items - 1  # 假设从行20开始
    ws.print_area = f'$A$1:$J${last_row}'
```

### 4.2 `_extend_packing_sheet` 方法

类似 `_extend_invoice_sheet`，但起始行和列数不同。

### 4.3 订舱单去重逻辑

```python
# 在 generate_booking 函数中
customs_names = fields.customs_names  # 原始列表
# 去重，保持顺序
unique_names = list(dict.fromkeys(customs_names))
# 填充到 DESC1-DESC6
for i, name in enumerate(unique_names[:6], 1):
    fields_dict[f"DESC{i}"] = name
```

---

## 5. 影响范围

### 5.1 需要修改的文件

| 文件 | 修改内容 |
|------|---------|
| `backend/app/services/document_service.py` | 新增 `_extend_invoice_sheet`、`_extend_packing_sheet` 方法 |
| `backend/app/api/v1/documents.py` | 修改 `generate_booking` 函数的去重逻辑 |
| `backend/tests/test_customs_dynamic_rows.py` | 新增发票/箱单扩展测试用例 |

### 5.2 模板文件

- `references/出口报关资料-模板.xlsx`：可能需要调整样式源位置
- `references/长晟出口海运BOOKING模板-已标记.xlsx`：无需修改

---

## 6. 测试计划

### 6.1 发票/箱单扩展测试

- N=10（< 预建）
- N=16（= 预建）
- N=20（扩展4行）
- N=38（扩展22行）
- 验证：边框、字体、对齐、打印区域、公式引用

### 6.2 订舱单去重测试

- 无同名产品
- 全部同名产品
- 部分同名产品
- 超过6个去重后产品

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 发票扩展后合同公式引用错位 | 合同Sheet数据错误 | 保持产品5起的起始行（行14）不变 |
| 箱单OFFSET公式引用失效 | 箱单数据错误 | 扩展后验证公式引用范围 |
| 订舱单去重后丢失信息 | 用户无法区分同名产品 | 订舱单只显示货名，详细信息在报关资料中 |
