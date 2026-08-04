# 报关资料按产品数动态扩展 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 报关资料生成时，报关单 sheet 按实际产品数动态向下新增产品块（超出模板预建的 6 块），不再截断。

**Architecture:** 在 `DocumentService.generate_customs` 中，当产品数 N > 6 时，以模板报关单第 6 块（行 35-37）为样式源，从第 38 行起逐块复制边框/行高/合并单元格并更新打印区域。N ≤ 6 时输出与现状完全一致。发票/箱单 sheet 与模板文件一律不动。

**Tech Stack:** Python 3, FastAPI, openpyxl, pytest

**设计文档:** `docs/superpowers/specs/2026-08-04-customs-dynamic-product-rows-design.md`

**测试命令（所有测试均从 backend 目录运行）:**
```bash
cd backend
python -m pytest tests/test_customs_dynamic_rows.py -v
```

---

### Task 1: 写失败测试（新增测试文件）

**Files:**
- Create: `backend/tests/test_customs_dynamic_rows.py`

背景知识：`generate_customs(ledger_record_id=...)` 内部调用 `LedgerService.get_ledger_record(record_id)` 读取台账。测试用 `monkeypatch` 替换该方法返回构造好的 `LedgerRecordResponse`，避免依赖真实数据库。`CustomsDeclarationService.get_instance()` 会连库加载申报要素（`declaration_elements` 表存在，可直接用）。模板文件 `references/出口报关资料-模板.xlsx` 在项目根目录，`TEMPLATES["customs"]` 指向它。

- [ ] **Step 1: 写测试文件**

```python
# backend/tests/test_customs_dynamic_rows.py
"""报关单 sheet 按产品数动态扩展的测试"""
import io
import openpyxl
import pytest

from app.services.document_service import DocumentService
from app.schemas.ledger import LedgerRecordResponse, LedgerItemSchema


def make_item(i: int) -> LedgerItemSchema:
    """构造第 i 个产品（1-based）"""
    return LedgerItemSchema(
        internal_code=f"SILI-{i:03d}",
        product_cn=f"有机硅柔软剂{i}",
        quantity_kg=1000.0 * i,
        unit_price=10.0,
        total_amount=10000.0 * i,
        hs_code="3910000000",
        customs_name=f"有机硅柔软剂{i}",
        customs_ingredients="八甲基环四硅氧烷50%,水50%",
        drum_count=2 * i,
        pallet_count=i,
        gross_weight_kg=1100.0 * i,
        net_weight_kg=1000.0 * i,
    )


def make_record(n_items: int) -> LedgerRecordResponse:
    return LedgerRecordResponse(
        id=1,
        order_no="HT260829E01",
        customer_code="TOA-DOVECHEM",
        sales_person="张三",
        consignee_name="ABC Co., Ltd.",
        consignee_address="123 Main St, Mumbai",
        destination="Nhava Sheva, India",
        loading_port="Shenzhen",
        price_term="CIF",
        payment_terms="T/T",
        pi_date="2026-08-01",
        currency="USD",
        items=[make_item(i) for i in range(1, n_items + 1)],
        status="saved",
    )


def generate_customs_bytes(monkeypatch, n_items: int) -> bytes:
    """调用 generate_customs 并返回生成的 xlsx 字节"""
    from app.services import ledger_service
    monkeypatch.setattr(
        ledger_service.LedgerService,
        "get_ledger_record",
        lambda self, record_id: make_record(n_items),
    )
    svc = DocumentService()
    content, _doc_key, _b64 = svc.generate_customs(ledger_record_id=1)
    return content


def load_customs_sheet(monkeypatch, n_items: int):
    wb = openpyxl.load_workbook(io.BytesIO(generate_customs_bytes(monkeypatch, n_items)))
    return wb["报关单"], wb


def test_n6_unchanged(monkeypatch):
    """N=6：模板预建容量内，不触发扩展，max_row 保持 37"""
    ws, _ = load_customs_sheet(monkeypatch, 6)
    assert ws.max_row == 37
    # 打印区域不变
    assert ws.print_area == "'报关单'!$A$1:$S$37"


def test_n7_adds_one_block(monkeypatch):
    """N=7：多出 1 块（3 行），max_row 变为 40"""
    ws, _ = load_customs_sheet(monkeypatch, 7)
    assert ws.max_row == 40
    assert ws.print_area == "'报关单'!$A$1:$S$40"
    # 第 7 个产品数据写入：项号=7, HS Code, 数量, 币制行
    assert ws.cell(38, 1).value == 7          # A38: 项号
    assert ws.cell(38, 2).value == "3910000000"  # B38: 商品编号
    assert ws.cell(38, 7).value == 7000.0     # G38: 数量
    assert ws.cell(40, 7).value == 7000.0     # G40: quantity reference
    assert ws.cell(40, 9).value == "美元"      # I40: 币制中文


def test_n17_many_blocks(monkeypatch):
    """N=17：共 17 块，max_row = 20 + 3*17 - 1 = 70"""
    ws, _ = load_customs_sheet(monkeypatch, 17)
    assert ws.max_row == 70
    assert ws.print_area == "'报关单'!$A$1:$S$70"
    assert ws.cell(68, 1).value == 17         # 最后一块数据行（20+16*3=68）
    assert ws.cell(68, 7).value == 17000.0


def test_extended_block_borders_and_merges(monkeypatch):
    """新块样式：边框与合并单元格必须与源块（第 6 块）一致"""
    ws, _ = load_customs_sheet(monkeypatch, 8)
    # 源块第 6 块：35/36/37 行；新块第 7 块：38/39/40 行
    # 边框抽样：数据行 A 列、申报行 D 列必须有 thin 边框
    assert ws.cell(38, 1).border.left.style is not None   # A38 边框
    assert ws.cell(39, 4).border.left.style is not None   # D39 申报要素行边框
    # 合并单元格：新块申报要素合并跨两行 D39:F40（对应源块 D36:F37）
    assert "D39:F40" in [str(r) for r in ws.merged_cells.ranges]
    # 数据行合并存在：B38:C38
    assert "B38:C38" in [str(r) for r in ws.merged_cells.ranges]


def test_n5_regression(monkeypatch):
    """N=5：小于预建容量，行为与扩展无关，数据正确写入"""
    ws, _ = load_customs_sheet(monkeypatch, 5)
    assert ws.max_row == 37
    assert ws.cell(20, 1).value == 1
    assert ws.cell(32, 1).value == 5
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_customs_dynamic_rows.py -v`
Expected: FAIL——`test_n7_adds_one_block` 断言 `ws.max_row == 40` 实际为 37（当前代码截断），`test_n17_many_blocks` 同理失败。其余测试通过或失败均可接受。

---

### Task 2: 实现扩展逻辑（修改 document_service.py）

**Files:**
- Modify: `backend/app/services/document_service.py`

- [ ] **Step 1: 新增私有方法 `_extend_customs_sheet`**

在 `generate_customs` 方法定义（第 827 行）之前插入以下方法。样式源块固定为模板第 6 块（行 35-37），该块必须存在，否则 raise：

```python
    @staticmethod
    def _extend_customs_sheet(ws, n_items: int) -> None:
        """
        报关单 sheet 按产品数动态扩展产品块（每品 3 行）。

        模板预建 6 块（行 20-37）。N > 6 时，以第 6 块（行 35-37）为样式源，
        从第 38 行起逐块复制边框/行高/合并单元格，并更新打印区域。
        仅复制样式与结构，不写任何数据（数据由 generate_customs 主体写入）。
        """
        import copy

        if n_items <= 6:
            return
        if ws.max_row < 37:
            raise ValueError(f"报关单模板预建块不足，max_row={ws.max_row}")

        src_rows = (35, 36, 37)          # 源块（第 6 块）三行
        n_new_blocks = n_items - 6
        for k in range(n_new_blocks):
            target = 38 + k * 3          # 新块起始行：38, 41, 44, ...
            for off in range(3):
                src = src_rows[off]
                dst = target + off
                # 复制行高
                if ws.row_dimensions[src].height:
                    ws.row_dimensions[dst].height = ws.row_dimensions[src].height
                # 逐单元格复制样式（A..S 列）
                for col in range(1, 20):
                    src_cell = ws.cell(src, col)
                    dst_cell = ws.cell(dst, col)
                    dst_cell._style = copy.copy(src_cell._style)
            # 复制合并单元格：源块所有合并区域偏移到本块位置
            # 每个新块独立偏移（target-35），不能一次性整体偏移
            row_offset = target - 35     # 第7块=3, 第8块=6, ...
            for mc in list(ws.merged_cells.ranges):
                if mc.min_row >= 35 and mc.max_row <= 37:
                    ws.merge_cells(
                        start_row=mc.min_row + row_offset,
                        start_column=mc.min_column,
                        end_row=mc.max_row + row_offset,
                        end_column=mc.max_column,
                    )

        # 更新打印区域
        last_row = 20 + 3 * n_items - 1
        ws.print_area = f"'报关单'!$A$1:$S${last_row}"
```

- [ ] **Step 2: 在 generate_customs 中调用扩展并放开截断**

修改 `document_service.py` 第 983-995 行区域。原文：

```python
        # 产品明细：每品占 3 行（数据行 / 申报要素行 / 公式行）
        # 起始行 = 20 + idx * 3，模板最多支持到行 37（约 5-6 个产品）
        max_items = (ws.max_row - 20) // 3
        if len(items) > max_items:
            import logging
            logging.warning(
                "报关单模板最多容纳 %d 个产品，当前 %d 个，多余产品将被截断",
                max_items, len(items),
            )
        for idx, item in enumerate(items):
            row = 20 + idx * 3
            if row + 2 > ws.max_row:
                break
```

改为：

```python
        # 产品明细：每品占 3 行（数据行 / 申报要素行 / 公式行）
        # 起始行 = 20 + idx * 3；超出模板预建 6 块时动态扩展
        self._extend_customs_sheet(ws, len(items))
        for idx, item in enumerate(items):
            row = 20 + idx * 3
```

- [ ] **Step 3: 放开 T/U/V 辅助列循环截断**

修改第一处辅助列循环（原第 1057-1062 行）。原文：

```python
        for idx, item in enumerate(items):
            if idx == 0:
                continue  # 第1个产品由箱单直接引用 F12/G20
            helper_row = 23 + (idx - 1) * 3  # 23, 26, 29, 32, 35
            if helper_row > ws.max_row:
                break
```

改为：

```python
        for idx, item in enumerate(items):
            if idx == 0:
                continue  # 第1个产品由箱单直接引用 F12/G20
            helper_row = 23 + (idx - 1) * 3  # 23, 26, 29, 32, ...
```

修改第二处辅助列循环（原第 1114-1120 行，位于发票填充之后）。原文：

```python
        for idx, item in enumerate(items):
            if idx == 0:
                continue  # 第1个产品由箱单直接引用 F12/G20
            # 箱单公式 ROW(V{4+idx})*3+16 = (4+idx)*3+16, 再+1偏移
            helper_row = 26 + idx * 3  # 29, 32, 35, 38, 41
            if helper_row > ws.max_row:
                break
```

改为：

```python
        for idx, item in enumerate(items):
            if idx == 0:
                continue  # 第1个产品由箱单直接引用 F12/G20
            # 箱单公式 ROW(V{4+idx})*3+16 = (4+idx)*3+16, 再+1偏移
            helper_row = 26 + idx * 3  # 29, 32, 35, 38, ...
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_customs_dynamic_rows.py -v`
Expected: 5 个测试全部 PASS。

- [ ] **Step 5: 回归运行全部测试**

Run: `python -m pytest tests/ -q`
Expected: 全部 PASS（现有测试不受影响）。

- [ ] **Step 6: 提交**

```bash
git add backend/tests/test_customs_dynamic_rows.py backend/app/services/document_service.py
git commit -m "feat: 报关单按产品数动态扩展，解除 6 产品上限"
```

---

### Task 3: 手动验证真实生成（可选但推荐）

**Files:**
- 无（仅运行验证脚本）

- [ ] **Step 1: 写一次性验证脚本并运行**

Run（backend 目录）:
```bash
python -c "
import io, openpyxl
from app.services.document_service import DocumentService
from app.schemas.ledger import LedgerRecordResponse, LedgerItemSchema
from app.services import ledger_service

def make_item(i):
    return LedgerItemSchema(internal_code=f'S-{i}', product_cn=f'产品{i}',
        quantity_kg=100.0*i, unit_price=5.0, total_amount=500.0*i,
        hs_code='3910000000', customs_name=f'有机硅柔软剂{i}',
        customs_ingredients='A50%,B50%', drum_count=i, pallet_count=i,
        gross_weight_kg=110.0*i, net_weight_kg=100.0*i)

rec = LedgerRecordResponse(id=1, order_no='HT260829E01', customer_code='C1',
    consignee_name='ABC', consignee_address='Addr', destination='Nhava Sheva, India',
    loading_port='Shenzhen', price_term='CIF', payment_terms='T/T',
    pi_date='2026-08-01', currency='USD',
    items=[make_item(i) for i in range(1, 13)], status='saved')
ledger_service.LedgerService.get_ledger_record = lambda self, rid: rec

svc = DocumentService()
content, key, _ = svc.generate_customs(ledger_record_id=1)
wb = openpyxl.load_workbook(io.BytesIO(content))
ws = wb['报关单']
print('max_row =', ws.max_row, '(expect 55)')
print('print_area =', ws.print_area)
print('last item 项号 =', ws.cell(53, 1).value, '(expect 12)')
print('D54:F55 merged =', 'D54:F55' in [str(r) for r in ws.merged_cells.ranges])
print('OK')
"
```
Expected: 输出 `max_row = 55`、`print_area = '报关单'!$A$1:$S$55`、`last item 项号 = 12`、`D54:F55 merged = True`、`OK`。

- [ ] **Step 2: 确认发票/箱单未受影响（抽样断言）**

在 Step 1 脚本基础上追加（同一命令行内）：

```bash
python -c "
import io, openpyxl
from app.services.document_service import DocumentService
from app.schemas.ledger import LedgerRecordResponse, LedgerItemSchema
from app.services import ledger_service

def make_item(i):
    return LedgerItemSchema(internal_code=f'S-{i}', product_cn=f'产品{i}',
        quantity_kg=100.0*i, unit_price=5.0, total_amount=500.0*i,
        hs_code='3910000000', customs_name=f'有机硅柔软剂{i}',
        customs_ingredients='A50%,B50%', drum_count=i, pallet_count=i,
        gross_weight_kg=110.0*i, net_weight_kg=100.0*i)

rec = LedgerRecordResponse(id=1, order_no='HT260829E01', customer_code='C1',
    consignee_name='ABC', consignee_address='Addr', destination='Nhava Sheva, India',
    loading_port='Shenzhen', price_term='CIF', payment_terms='T/T',
    pi_date='2026-08-01', currency='USD',
    items=[make_item(i) for i in range(1, 13)], status='saved')
ledger_service.LedgerService.get_ledger_record = lambda self, rid: rec

svc = DocumentService()
content, key, _ = svc.generate_customs(ledger_record_id=1)
wb = openpyxl.load_workbook(io.BytesIO(content))
inv, pkg = wb['发票'], wb['箱单']
print('发票 max_row =', inv.max_row, '(expect 31, 模板原样)')
print('箱单 max_row =', pkg.max_row, '(expect 28, 模板原样)')
print('箱单 SUM 公式 =', pkg['C26'].value, '(expect =SUM(C10:C25), 未变)')
print('OK')
"
```
Expected: 发票 max_row=31、箱单 max_row=28、箱单 C26 仍为 `=SUM(C10:C25)`。确认发票/箱单未被扩展逻辑触碰。

---

### Task 4: 自审清单

- [ ] **Step 1: 对照设计文档核查**

逐项核对设计文档 §5.2/§5.3：块复制（边框/行高/合并/打印区域）已实现；三处截断（`:994` 产品行、`:1061` 第一处辅助列、`:1119` 第二处辅助列）均已放开；发票/箱单与模板零改动。

- [ ] **Step 2: 占位符扫描**

在 `backend/app/services/document_service.py` 与测试文件中搜索 `TBD|TODO|XXX|pass  # 待`，确认无残留。

- [ ] **Step 3: 类型/命名一致性**

确认 `_extend_customs_sheet(ws, n_items)` 签名在调用处（`self._extend_customs_sheet(ws, len(items))`）与定义处一致；测试中 `make_item` / `make_record` / `load_customs_sheet` 名称与引用一致。
