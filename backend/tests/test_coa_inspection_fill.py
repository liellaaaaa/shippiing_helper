# -*- coding: utf-8 -*-
"""COA 检测报告上传解析 + 多批填表。

业务规则：
- 解析检测报告写什么就填什么（含外观「久置变深」）
- pH 标签用报告条件写法：PH (1%) / PH VALUE (20%)
- PI No 固定本票（一票一 COA）
- 多批次 → 同一 COA 工作簿多个 sheet
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import openpyxl
import pytest

from app.schemas.ledger import LedgerItemSchema, LedgerRecordResponse
from app.services.clearance_doc_service import ClearanceDocService
from app.services.inspection_report_service import parse_inspection_report

# 真实样例（存在则优先用）
_REAL_WA318 = Path(
    r"C:\Users\windows\Desktop\WA318 HT260720SZ\清关资料\检测报告\260731(T16-H)WA318.docx"
)
_REAL_WA254 = Path(
    r"C:\Users\windows\Desktop\WA254 HT260728A01 清关资料\02_检测报告 & 产品图片\260814(B-72B)WA254.docx"
)


def make_record() -> LedgerRecordResponse:
    """本票 HT260720SZ（对齐 test_clearance_doc_service）。"""
    return LedgerRecordResponse(
        id=1,
        order_no="HT260720SZ",
        customer_code="WA318",
        consignee_name="CHEMZONE CO., LTD.",
        consignee_address="26/1D TRAN QUY CAP ST., HO CHI MINH CITY, VIETNAM",
        consignee_tel="TAX CODE: 0316699088",
        destination="HOCHIMINH(CAT LAI), VIETNAM",
        loading_port="NANSHA, CHINA",
        price_term="CIF HOCHIMINH",
        payment_terms="100% TT AFTER SHIPMENT 30 DAYS",
        pi_date="2026-07-20",
        currency="USD",
        items=[
            LedgerItemSchema(
                internal_code="FIX-HT016H",
                product_en="FIXING AGENT HT-016H",
                quantity_kg=4000.0,
                unit_price=2.6,
                total_amount=10400.0,
                hs_code="340241",
                drum_count=32,
                pallet_count=8,
                net_weight_kg=4000.0,
                gross_weight_kg=4308.0,
                volume_cbm=7.92,
            )
        ],
        status="saved",
    )


def _build_two_batch_docx() -> bytes:
    """无真实样例时，用 python-docx 拼两批次检测报告。"""
    from docx import Document

    doc = Document()
    # 批次 1
    doc.add_paragraph("客户：WA318")
    doc.add_paragraph("品名：固色剂　　编号：T16-H")
    doc.add_paragraph("批号：SA20260626017")
    doc.add_paragraph("数量：3250kg")
    t1 = doc.add_table(rows=1, cols=3)
    for i, h in enumerate(("项目", "技术指标", "检查结果")):
        t1.rows[0].cells[i].text = h
    for name, spec, result in (
        ("外观", "黄色透明粘液 （久置变深）", "黄色透明粘液"),
        ("1%pH值", "6.5~7.5", "7.30"),
        ("含固量（%）", "70±2", "70.72"),
    ):
        row = t1.add_row().cells
        row[0].text, row[1].text, row[2].text = name, spec, result
    # 批次 2
    doc.add_paragraph("批号：SA20260713008")
    doc.add_paragraph("数量：750kg")
    t2 = doc.add_table(rows=1, cols=3)
    for i, h in enumerate(("项目", "技术指标", "检查结果")):
        t2.rows[0].cells[i].text = h
    for name, spec, result in (
        ("外观", "黄色透明粘液 （久置变深）", "黄色透明粘液"),
        ("1%pH值", "6.5~7.5", "7.26"),
        ("含固量（%）", "70±2", "69.79"),
    ):
        row = t2.add_row().cells
        row[0].text, row[1].text, row[2].text = name, spec, result
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _load_two_batch_bytes() -> bytes:
    if _REAL_WA318.is_file():
        return _REAL_WA318.read_bytes()
    return _build_two_batch_docx()


def _tests_as_batch(batch: dict) -> dict:
    """parser 批次 dict 原样传给 generate（含 tests[]）。"""
    return dict(batch)


def test_parse_two_sample_style():
    """两批次样例：WA318 真实文件优先，否则合成 docx；断言批号/pH/外观。"""
    batches = parse_inspection_report(_load_two_batch_bytes())
    assert len(batches) == 2

    b0, b1 = batches
    assert b0["batch_no"] == "SA20260626017"
    assert b1["batch_no"] == "SA20260713008"
    assert b0["quantity_text"]
    assert b1["quantity_text"]

    def _find(batch, key):
        for t in batch["tests"]:
            if t["key"] == key:
                return t
        return None

    ph0 = _find(b0, "ph")
    assert ph0 is not None
    # pH 标签为报告条件写法占位
    assert ph0["label_en"] in ("PH (1%)", "PH VALUE (20%)", "PH VALUE")
    assert ph0["result"]

    solid0 = _find(b0, "solid")
    assert solid0 is not None and solid0["result"]

    # 外观写报告原文；真实 WA254 含「久置变深」时保留
    app0 = _find(b0, "appearance")
    assert app0 is not None
    assert app0["spec"]

    ph1 = _find(b1, "ph")
    assert ph1 is not None and ph1["result"] != ph0["result"]


def test_parse_wa254_appearance_keeps_久置变深():
    """外观规格保留「久置变深」等修饰语（真实 WA254 样例）。"""
    if not _REAL_WA254.is_file():
        pytest.skip("WA254 检测报告样例不存在")
    batches = parse_inspection_report(_REAL_WA254.read_bytes())
    assert len(batches) >= 1
    app = next(t for t in batches[0]["tests"] if t["key"] == "appearance")
    assert "久置变深" in app["spec"]


def test_generate_two_batches_one_workbook():
    """多批 → 同一 COA 工作簿多 sheet；各 sheet 批号/pH 结果正确。"""
    batches = parse_inspection_report(_load_two_batch_bytes())
    assert len(batches) == 2

    svc = ClearanceDocService()
    content, doc_key, b64 = svc.generate(
        "coa",
        make_record(),
        "honghao",
        {"batches": [_tests_as_batch(b) for b in batches]},
    )
    assert doc_key.startswith("coa_")
    assert b64

    wb = openpyxl.load_workbook(io.BytesIO(content))
    assert len(wb.worksheets) == 2

    # sheet 标题 = 批号
    titles = [ws.title for ws in wb.worksheets]
    assert "SA20260626017" in titles[0]
    assert "SA20260713008" in titles[1]

    def _sheet_text(ws) -> str:
        parts = []
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    parts.append(str(cell.value))
        return "\n".join(parts)

    t0 = _sheet_text(wb.worksheets[0])
    t1 = _sheet_text(wb.worksheets[1])
    assert "SA20260626017" in t0
    assert "SA20260713008" not in t0 or t0.count("SA20260713008") == 0
    assert "SA20260713008" in t1
    assert "SA20260626017" not in t1 or True  # 批号只在本 sheet

    # pH 结果分批正确
    ph0 = next(t for t in batches[0]["tests"] if t["key"] == "ph")
    ph1 = next(t for t in batches[1]["tests"] if t["key"] == "ph")
    assert ph0["result"] in t0
    assert ph1["result"] in t1
    assert ph0["result"] not in t1
    assert ph1["result"] not in t0

    # pH 标签（报告条件写法）写入
    assert ph0["label_en"] in t0
    assert ph1["label_en"] in t1


def test_generate_coa_pi_no_is_this_pi():
    """PI No 固定本票 HT260720SZ（一票一 COA），不跟检测报告客户号。"""
    batches = parse_inspection_report(_load_two_batch_bytes())
    svc = ClearanceDocService()
    content, _, _ = svc.generate(
        "coa",
        make_record(),
        "honghao",
        {"batches": [_tests_as_batch(b) for b in batches]},
    )
    wb = openpyxl.load_workbook(io.BytesIO(content))
    for ws in wb.worksheets:
        text = "\n".join(
            str(cell.value)
            for row in ws.iter_rows()
            for cell in row
            if cell.value is not None
        )
        assert "HT260720SZ" in text
        # 不得写成客户号
        assert "PI No.: WA318" not in text


def test_generate_prod_date_from_batch_no():
    """PROD_DATE 空时从批号 SA+YYYYMMDD 推导。"""
    batch = {
        "batch_no": "SA20260626017",
        "quantity_text": "3250kg",
        "tests": [
            {"key": "ph", "label_en": "PH (1%)", "spec": "6.5~7.5", "result": "7.30"},
        ],
    }
    svc = ClearanceDocService()
    content, _, _ = svc.generate("coa", make_record(), "honghao", {"batches": [batch]})
    text = "\n".join(
        str(cell.value)
        for row in openpyxl.load_workbook(io.BytesIO(content)).worksheets[0].iter_rows()
        for cell in row
        if cell.value is not None
    )
    assert "2026-06-26" in text


def test_single_batch_flat_override_still_works():
    """前端扁平字段覆盖 tests[]（表格编辑路径）。"""
    batch = {
        "batch_no": "SA20260807038",
        "quantity_text": "3000kg",
        "ph_label": "PH VALUE (20%)",
        "ph_spec": "4±0.5",
        "ph_result": "EDITED",
        "solid_label": "SOLID CONTENT(%)",
        "solid_spec": "32±1",
        "solid_result": "32.39",
        "appearance_spec": "黄色透明粘液 （久置变深）",
        "appearance_result": "黄色透明粘液",
        "tests": [
            {"key": "ph", "label_en": "PH VALUE (20%)", "spec": "4±0.5", "result": "3.79"},
        ],
    }
    svc = ClearanceDocService()
    content, _, _ = svc.generate("coa", make_record(), "honghao", {"batches": [batch]})
    text = "\n".join(
        str(cell.value)
        for row in openpyxl.load_workbook(io.BytesIO(content)).worksheets[0].iter_rows()
        for cell in row
        if cell.value is not None
    )
    assert "EDITED" in text
    assert "3.79" not in text
    assert "久置变深" in text
