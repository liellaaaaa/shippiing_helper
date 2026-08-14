# 报关资料动态扩展 & 订舱单同名合并 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现发票/箱单Sheet动态扩展行数，以及订舱单按产品中文名去重合并

**Architecture:** 
- 发票和箱单采用与报关单相同的扩展逻辑（`_extend_customs_sheet`模式）
- 订舱单在后端填充时按 `product_cn` 去重，保持模板不变

**Tech Stack:** Python, openpyxl, FastAPI

---

## 文件结构

| 文件 | 修改类型 | 职责 |
|------|---------|------|
| `backend/app/services/document_service.py` | 修改 | 新增 `_extend_invoice_sheet`、`_extend_packing_sheet` 方法 |
| `backend/app/api/v1/documents.py` | 修改 | `generate_booking` 函数添加去重逻辑 |
| `backend/tests/test_customs_dynamic_rows.py` | 修改 | 新增发票/箱单扩展测试用例 |
| `backend/tests/test_booking_dedup.py` | 新增 | 订舱单去重测试 |

---

## Task 1: 理解现有报关单扩展逻辑

**Files:**
- Read: `backend/app/services/document_service.py:608-653`

- [ ] **Step 1: 阅读 `_extend_customs_sheet` 方法**

阅读 `document_service.py` 第608-653行，理解：
- 预建容量：6块（每块3行，共18行）
- 样式源：第6块（行35-37）
- 扩展方式：逐块复制样式/行高/合并单元格
- 打印区域更新

- [ ] **Step 2: 阅读发票Sheet填充逻辑**

阅读 `generate_customs` 方法中发票Sheet的填充部分，理解：
- 产品1-4在行8-11
- 产品5起跳过预留行12/13，从行14开始
- 最大行：行23（共16个产品容量）
- 汇总行：行24

- [ ] **Step 3: 阅读箱单Sheet填充逻辑**

阅读 `generate_customs` 方法中箱单Sheet的填充部分，理解：
- 产品行从第10行开始
- 最大行：行25（共16个产品容量）
- 汇总行：行26
- 数据来源：部分通过OFFSET公式引用报关单Sheet

---

## Task 2: 实现 `_extend_invoice_sheet` 方法

**Files:**
- Modify: `backend/app/services/document_service.py`
- Test: `backend/tests/test_customs_dynamic_rows.py`

- [ ] **Step 1: 编写发票扩展测试用例**

在 `test_customs_dynamic_rows.py` 中添加：

```python
def test_invoice_sheet_extension():
    """测试发票Sheet动态扩展"""
    # 准备：创建模拟的发票Sheet
    # 验证：N=10, N=16, N=20, N=38 各种情况
    # 验证：边框、字体、对齐、打印区域
    pass
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && pytest tests/test_customs_dynamic_rows.py::test_invoice_sheet_extension -v
```

预期：FAIL（方法不存在）

- [ ] **Step 3: 实现 `_extend_invoice_sheet` 方法**

在 `document_service.py` 中添加：

```python
def _extend_invoice_sheet(self, ws, n_items: int):
    """动态扩展发票Sheet行数
    
    预建容量：16行（行8-23）
    扩展触发：N > 16
    样式源：最后一行产品行（行23）
    """
    prebuilt = 16
    if n_items <= prebuilt:
        return
    
    # 样式源：行23
    source_row = 23
    # 起始插入行：行24（汇总行之前）
    start_row = 24
    
    # 计算需要插入的行数
    rows_to_insert = n_items - prebuilt
    
    # 插入空行
    ws.insert_rows(start_row, rows_to_insert)
    
    # 复制样式
    for i in range(rows_to_insert):
        target_row = start_row + i
        for col in range(1, 11):  # A-J列
            source_cell = ws.cell(row=source_row, column=col)
            target_cell = ws.cell(row=target_row, column=col)
            self._copy_cell_style(source_cell, target_cell)
        # 复制行高
        ws.row_dimensions[target_row].height = ws.row_dimensions[source_row].height
    
    # 更新打印区域（假设从行8开始）
    last_row = 8 + n_items - 1
    ws.print_area = f'$A$1:$J${last_row}'
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && pytest tests/test_customs_dynamic_rows.py::test_invoice_sheet_extension -v
```

预期：PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/document_service.py backend/tests/test_customs_dynamic_rows.py
git commit -m "feat: add invoice sheet dynamic extension"
```

---

## Task 3: 实现 `_extend_packing_sheet` 方法

**Files:**
- Modify: `backend/app/services/document_service.py`
- Test: `backend/tests/test_customs_dynamic_rows.py`

- [ ] **Step 1: 编写箱单扩展测试用例**

在 `test_customs_dynamic_rows.py` 中添加：

```python
def test_packing_sheet_extension():
    """测试箱单Sheet动态扩展"""
    # 准备：创建模拟的箱单Sheet
    # 验证：N=10, N=16, N=20, N=38 各种情况
    # 验证：边框、字体、对齐、打印区域
    pass
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && pytest tests/test_customs_dynamic_rows.py::test_packing_sheet_extension -v
```

预期：FAIL（方法不存在）

- [ ] **Step 3: 实现 `_extend_packing_sheet` 方法**

在 `document_service.py` 中添加：

```python
def _extend_packing_sheet(self, ws, n_items: int):
    """动态扩展箱单Sheet行数
    
    预建容量：16行（行10-25）
    扩展触发：N > 16
    样式源：最后一行产品行（行25）
    """
    prebuilt = 16
    if n_items <= prebuilt:
        return
    
    # 样式源：行25
    source_row = 25
    # 起始插入行：行26（汇总行之前）
    start_row = 26
    
    # 计算需要插入的行数
    rows_to_insert = n_items - prebuilt
    
    # 插入空行
    ws.insert_rows(start_row, rows_to_insert)
    
    # 复制样式
    for i in range(rows_to_insert):
        target_row = start_row + i
        for col in range(1, 11):  # A-J列
            source_cell = ws.cell(row=source_row, column=col)
            target_cell = ws.cell(row=target_row, column=col)
            self._copy_cell_style(source_cell, target_cell)
        # 复制行高
        ws.row_dimensions[target_row].height = ws.row_dimensions[source_row].height
    
    # 更新打印区域（假设从行10开始）
    last_row = 10 + n_items - 1
    ws.print_area = f'$A$1:$J${last_row}'
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && pytest tests/test_customs_dynamic_rows.py::test_packing_sheet_extension -v
```

预期：PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/document_service.py backend/tests/test_customs_dynamic_rows.py
git commit -m "feat: add packing sheet dynamic extension"
```

---

## Task 4: 集成扩展方法到 `generate_customs`

**Files:**
- Modify: `backend/app/services/document_service.py`

- [ ] **Step 1: 在 `generate_customs` 中调用扩展方法**

在填充发票Sheet之前添加：

```python
# 动态扩展发票Sheet
self._extend_invoice_sheet(ws_invoice, len(items))

# 动态扩展箱单Sheet
self._extend_packing_sheet(ws_packing, len(items))
```

- [ ] **Step 2: 运行现有测试**

```bash
cd backend && pytest tests/test_customs_dynamic_rows.py -v
```

预期：所有测试通过

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/document_service.py
git commit -m "feat: integrate invoice/packing sheet extension into generate_customs"
```

---

## Task 5: 实现订舱单同名合并

**Files:**
- Modify: `backend/app/api/v1/documents.py`
- New: `backend/tests/test_booking_dedup.py`

- [ ] **Step 1: 编写订舱单去重测试**

创建 `test_booking_dedup.py`：

```python
def test_booking_dedup_by_product_cn():
    """测试订舱单按产品中文名去重"""
    # 场景1：无同名产品
    customs_names = ["防染剂", "柔软剂", "分散剂"]
    expected = ["防染剂", "柔软剂", "分散剂"]
    
    # 场景2：全部同名
    customs_names = ["防染剂", "防染剂", "防染剂"]
    expected = ["防染剂"]
    
    # 场景3：部分同名
    customs_names = ["防染剂", "防染剂", "柔软剂", "分散剂"]
    expected = ["防染剂", "柔软剂", "分散剂"]
    
    # 场景4：超过6个去重后产品
    customs_names = ["A", "B", "C", "D", "E", "F", "G"]
    expected = ["A", "B", "C", "D", "E", "F"]  # 只取前6个
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend && pytest tests/test_booking_dedup.py -v
```

预期：FAIL

- [ ] **Step 3: 修改 `generate_booking` 函数**

在 `documents.py` 的 `generate_booking` 函数中，找到构建 `customs_names` 的代码：

```python
# 原代码
for i, name in enumerate(fields.customs_names, 1):
    fields_dict[f"DESC{i}"] = name
```

修改为：

```python
# 去重，保持顺序
unique_names = list(dict.fromkeys(fields.customs_names))
# 填充到DESC1-DESC6
for i, name in enumerate(unique_names[:6], 1):
    fields_dict[f"DESC{i}"] = name
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend && pytest tests/test_booking_dedup.py -v
```

预期：PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/v1/documents.py backend/tests/test_booking_dedup.py
git commit -m "feat: add booking confirmation same-name product deduplication"
```

---

## Task 6: 端到端测试

**Files:**
- Test: 手动测试

- [ ] **Step 1: 测试发票/箱单扩展**

1. 创建一个包含38个产品的订单
2. 生成报关资料
3. 验证发票Sheet：38行产品数据，样式正确
4. 验证箱单Sheet：38行产品数据，样式正确
5. 验证合同Sheet：公式引用正确

- [ ] **Step 2: 测试订舱单去重**

1. 创建一个包含多个同名产品的订单
2. 生成订舱单
3. 验证：同名产品只显示一行
4. 验证：毛重/体积为汇总值

- [ ] **Step 3: 提交最终版本**

```bash
git add .
git commit -m "feat: complete customs dynamic extension and booking dedup"
```

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 发票扩展后合同公式引用错位 | 保持产品5起的起始行（行14）不变 |
| 箱单OFFSET公式引用失效 | 扩展后验证公式引用范围 |
| 订舱单去重后丢失信息 | 订舱单只显示货名，详细信息在报关资料中 |
