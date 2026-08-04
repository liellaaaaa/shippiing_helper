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
    # 边框抽样：数据行 A 列、申报行 A 列必须有 thin 边框
    assert ws.cell(38, 1).border.left.style is not None   # A38 边框
    assert ws.cell(39, 1).border.left.style is not None   # A39 申报要素行边框
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
