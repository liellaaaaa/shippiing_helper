# -*- coding: utf-8 -*-
"""从成品清关单副本生成公共模板：只替换动态字段为 {{占位符}}，保留原版式。

素材：C:\\Users\\windows\\Desktop\\清关样例_已转xlsx\\
  WA318: CI / PL / COA（宏昊标准抬头）
  WA254: 对照（客户差异走 customer_templates）
SI 无 xlsx 成品（仅 BL PDF）：用 PL 成品壳 + 补料字段占位符。

运行: cd backend && python -m scripts.build_clearance_templates
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = Path(r"C:\Users\windows\Desktop\清关样例_已转xlsx")
OUT = ROOT / "references" / "clearance"

WA318 = SAMPLES / "WA318"
WA254 = SAMPLES / "WA254"


def _keep_sheet(wb, prefer: str | None):
    if prefer:
        for ws in wb.worksheets:
            if prefer.lower() in ws.title.lower().replace(" ", ""):
                for other in list(wb.worksheets):
                    if other is not ws:
                        wb.remove(other)
                return ws
    # 取内容最多的
    best = max(wb.worksheets, key=lambda w: sum(
        1 for row in w.iter_rows() for c in row if c.value is not None
    ))
    for other in list(wb.worksheets):
        if other is not best:
            wb.remove(other)
    return best


def _patch_text(ws, rules: list[tuple[str, str]]):
    for row in ws.iter_rows():
        for cell in row:
            if not isinstance(cell.value, str):
                continue
            s = cell.value
            for a, b in rules:
                if a in s:
                    s = s.replace(a, b)
            if s != cell.value:
                cell.value = s


def _patch_numbers(ws, rules: list[tuple[object, str]]):
    mapping = dict(rules)
    for row in ws.iter_rows():
        for cell in row:
            if cell.value in mapping:
                cell.value = mapping[cell.value]


def _replace_bank_block(ws):
    """银行 6 行 → 占位（支持 show_bank_block）。"""
    for row in ws.iter_rows():
        for cell in row:
            if not isinstance(cell.value, str):
                continue
            t = cell.value.upper()
            if "BENEFICIARY BANK :" in t or "BENEFICIARY BANK:" in t:
                cell.value = "{{BANK_LINE1}}"
            elif "BANK ADDRESS" in t and "BENEFICIARY" in t or t.startswith("BEBEFICIARY BANK ADDRESS"):
                cell.value = "{{BANK_LINE2}}"
            elif "BENEFICIARY NAME" in t:
                cell.value = "{{BANK_LINE3}}"
            elif "COMPANY ADDRESS" in t and "BENEFICIARY" in t:
                cell.value = "{{BANK_LINE4}}"
            elif "BANK A/C" in t or "BANK AC" in t:
                cell.value = "{{BANK_LINE5}}"
            elif "SWIFT" in t:
                cell.value = "{{BANK_LINE6}}"


def build_ci():
    src = WA318 / "CI-HT260720SZ.xlsx"
    shutil.copy2(src, OUT / "CI-public.xlsx")
    wb = load_workbook(OUT / "CI-public.xlsx")
    ws = _keep_sheet(wb, "invoice")
    ws.title = "CI"
    _patch_text(ws, [
        ("FROM NANSHA, CHINA TO  HOCHIMINH(CAT LAI),VIETNAM", "{{ROUTE}}"),
        ("WHLU5694625", "{{CONTAINER_NO}}"),
        ("WHA4051188", "{{SEAL_NO}}"),
        ("CHEMZONE CO., LTD.", "{{CONSIGNEE_NAME}}"),
        ("26/1D TRAN QUY CAP ST., BINH LOI TRUNG WARD, HO CHI MINH CITY, VIETNAM", "{{CONSIGNEE_ADDR}}"),
        ("TAX CODE: 0316699088", "{{CONSIGNEE_TAX}}"),
        ("IN260720SZ", "{{INVOICE_NO}}"),
        ("HT260720SZ", "{{PI_NO}}"),
        ("CIF  HOCHIMINH", "{{PRICE_TERM}}"),
        ("FIXING AGENT HT-016H", "{{ITEM_DESC}}"),
        ("QTY:4000KGS", "QTY:{{TOTAL_QTY}}KGS"),
        ("HS CODE:340241", "HS CODE:{{HS_CODES}}"),
        ("TOTAL 32 DRUMS PACKED ON 8 PALLETS ONLY.", "{{TOTALS_LINE}}"),
        ("PAYMENT TERMS: 100% TT AFTER SHIPMENT 30 DAYS", "PAYMENT TERMS: {{PAYMENT_TERMS}}"),
        ("TOTAL USD TEN THOUSAND AND FOUR HUNDRED ONLY", "{{AMOUNT_WORDS}}"),
    ])
    _replace_bank_block(ws)
    # 日期/明细数字/公式
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "2026-08-01" in cell.value:
                cell.value = cell.value.replace("2026-08-01", "{{INVOICE_DATE}}")
            if cell.value in (4000, 4000.0) and cell.column == 3:
                cell.value = "{{ITEM_QTY}}" if cell.row < 25 else "{{TOTAL_QTY}}"
            if cell.value in (2.6, 2.60) and cell.column == 4:
                cell.value = "{{ITEM_PRICE}}"
            if cell.value in (10400, 10400.0) and cell.column in (5, 6):
                cell.value = "{{ITEM_AMOUNT}}" if cell.row < 25 else "{{TOTAL_AMOUNT}}"
            if isinstance(cell.value, str) and cell.value.startswith("=C"):
                cell.value = "{{ITEM_AMOUNT}}"
            if isinstance(cell.value, str) and cell.value.startswith("=SUM(C"):
                cell.value = "{{TOTAL_QTY}}"
            if isinstance(cell.value, str) and cell.value.startswith("=SUM(E"):
                cell.value = "{{TOTAL_AMOUNT}}"
    wb.save(OUT / "CI-public.xlsx")
    print("CI <-", src.name)


def build_pl():
    src = WA318 / "PL-HT260720SZ.xlsx"
    shutil.copy2(src, OUT / "PL-public.xlsx")
    wb = load_workbook(OUT / "PL-public.xlsx")
    ws = _keep_sheet(wb, "pl")
    ws.title = "PL"
    _patch_text(ws, [
        ("FROM NANSHA, CHINA TO  HOCHIMINH(CAT LAI),VIETNAM", "{{ROUTE}}"),
        ("WHLU5694625", "{{CONTAINER_NO}}"),
        ("WHA4051188", "{{SEAL_NO}}"),
        ("CHEMZONE CO., LTD.", "{{CONSIGNEE_NAME}}"),
        ("26/1D TRAN QUY CAP ST., BINH LOI TRUNG WARD, HO CHI MINH CITY, VIETNAM", "{{CONSIGNEE_ADDR}}"),
        ("TAX CODE: 0316699088", "{{CONSIGNEE_TAX}}"),
        ("PL260720SZ", "{{PACKING_NO}}"),
        ("HT260720SZ", "{{PI_NO}}"),
        ("FIXING AGENT HT-016H", "{{ITEM_DESC}}"),
        ("QTY:4000KGS", "QTY:{{TOTAL_QTY}}KGS"),
        ("HS CODE:340241", "HS CODE:{{HS_CODES}}"),
        ("TOTAL 32 DRUMS PACKED ON 8 PALLETS ONLY.", "{{TOTALS_LINE}}"),
    ])
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "2026-08-01" in cell.value:
                cell.value = cell.value.replace("2026-08-01", "{{INVOICE_DATE}}")
            if cell.value in (8, 8.0) and cell.column == 3:
                cell.value = "{{PACKAGES}}" if cell.row < 25 else "{{PACKAGES}}"
            if cell.value in (7.92, 7.920) and cell.column == 4:
                cell.value = "{{VOLUME_CBM}}"
            if cell.value in (4000, 4000.0) and cell.column == 5:
                cell.value = "{{NET_KG}}"
            if cell.value in (4308, 4308.0) and cell.column == 6:
                cell.value = "{{GROSS_KG}}"
            if isinstance(cell.value, str) and cell.value.startswith("=SUM(C"):
                cell.value = "{{PACKAGES}}"
            if isinstance(cell.value, str) and cell.value.startswith("=SUM(D"):
                cell.value = "{{VOLUME_CBM}}"
            if isinstance(cell.value, str) and cell.value.startswith("=SUM(E"):
                cell.value = "{{NET_KG}}"
            if isinstance(cell.value, str) and cell.value.startswith("=SUM(F"):
                cell.value = "{{GROSS_KG}}"
    wb.save(OUT / "PL-public.xlsx")
    print("PL <-", src.name)


def build_coa():
    # WA254 COA 版式更干净（单 sheet）
    src = WA254 / "COA of HT825G (PO#JX3352-26070017).xlsx"
    shutil.copy2(src, OUT / "COA-public.xlsx")
    wb = load_workbook(OUT / "COA-public.xlsx")
    ws = _keep_sheet(wb, None)
    ws.title = "COA"
    _patch_text(ws, [
        ("WET RUBBING FASTNESS IMPROVING AGENT WRF HT825G", "{{PRODUCT_NAME}}"),
        ("3000kg", "{{SHIPPED_QTY}}"),
        ("3000KG", "{{SHIPPED_QTY}}"),
        ("SA20260807038", "{{BATCH_NO}}"),
        ("2026-08-07", "{{PROD_DATE}}"),
        ("2027-02-06", "{{EXP_DATE}}"),
        ("Yellow transparent mucus （久置变深）", "{{APPEARANCE_SPEC}}"),
        ("Yellow transparent mucus", "{{APPEARANCE_SPEC}}"),
        ("Slight odour", "{{ODOUR_SPEC}}"),
        ("32±1", "{{SOLID_SPEC}}"),
        ("4±0.5", "{{PH_SPEC}}"),
        ("PH VALUE (20%)", "{{PH_LABEL}}"),
        ("SOLID CONTENT(%)", "{{SOLID_LABEL}}"),
    ])
    # 数值格（openpyxl 可能读成 float，文本替换打不中）
    for row in ws.iter_rows():
        for cell in row:
            if cell.value in (32.39, "32.39"):
                cell.value = "{{SOLID_RESULT}}"
            elif cell.value in (3.79, "3.79"):
                cell.value = "{{PH_RESULT}}"
            elif cell.value in (3000, 3000.0) and str(cell.value) != "{{SHIPPED_QTY}}":
                # 数量格
                if "{{SHIPPED_QTY}}" not in str(ws.cell(cell.row, 1).value or ""):
                    pass
            if isinstance(cell.value, str) and "Slight odour" in cell.value and cell.column >= 5:
                cell.value = "{{ODOUR_RESULT}}"
    # 外观两列
    seen = 0
    for row in ws.iter_rows():
        for cell in row:
            if cell.value == "{{APPEARANCE_SPEC}}":
                seen += 1
                if seen == 2:
                    cell.value = "{{APPEARANCE_RESULT}}"
            if cell.value == "{{ODOUR_SPEC}}":
                pass
    seen_odo = 0
    for row in ws.iter_rows():
        for cell in row:
            if cell.value == "{{ODOUR_SPEC}}":
                seen_odo += 1
                if seen_odo == 2:
                    cell.value = "{{ODOUR_RESULT}}"
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "PI No" in cell.value:
                cell.value = "PI No.: {{COA_PI_NO}}"
    # WA254 原件可能无 PI No 行 —— 补一行（与 WA318 对齐）
    has_pi = any(
        isinstance(c.value, str) and "{{COA_PI_NO}}" in c.value
        for row in ws.iter_rows()
        for c in row
    )
    if not has_pi:
        # 在 BATCH 行所在行的空列写入，或追加到 QUANTITY 行文本
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and "{{BATCH_NO}}" in cell.value:
                    cell.value = cell.value + "    PI No.: {{COA_PI_NO}}"
                    has_pi = True
                    break
            if has_pi:
                break
    wb.save(OUT / "COA-public.xlsx")
    print("COA <-", src.name)


def build_si():
    """SI 用 PL 成品壳（同属装箱/补料版式），标题改为补料单。"""
    src = WA318 / "PL-HT260720SZ.xlsx"
    shutil.copy2(src, OUT / "SI-public.xlsx")
    wb = load_workbook(OUT / "SI-public.xlsx")
    ws = _keep_sheet(wb, "pl")
    ws.title = "SI"
    _patch_text(ws, [
        ("PACKING LIST", "BOOKING / SHIPPING INSTRUCTION (SI)"),
        ("（订舱补料 — 非提单正本；正本由船公司签发）", ""),
        ("FROM NANSHA, CHINA TO  HOCHIMINH(CAT LAI),VIETNAM", "{{ROUTE}}"),
        ("WHLU5694625", "{{CONTAINER_NO}}"),
        ("WHA4051188", "{{SEAL_NO}}"),
        ("CHEMZONE CO., LTD.", "{{CONSIGNEE_NAME}}"),
        ("26/1D TRAN QUY CAP ST., BINH LOI TRUNG WARD, HO CHI MINH CITY, VIETNAM", "{{CONSIGNEE_ADDR}}"),
        ("TAX CODE: 0316699088", "{{CONSIGNEE_TAX}}"),
        ("SAME AS CONSIGNEE", "{{NOTIFY}}"),
        ("PL260720SZ", "{{BL_NO}}"),
        ("HT260720SZ", "{{PI_NO}}"),
        ("FIXING AGENT HT-016H", "{{ITEM_DESC}}"),
        ("QTY:4000KGS", "QTY:{{SHIPPED_QTY}}"),
        ("HS CODE:340241", "HS CODE:{{HS_CODES}}"),
        ("TOTAL 32 DRUMS PACKED ON 8 PALLETS ONLY.", "{{TOTALS_LINE}}"),
    ])
    _patch_text(ws, [
        ("CONTAINER NO.: {{CONTAINER_NO}}", "VESSEL / VOYAGE: {{VESSEL}}    CONTAINER NO.: {{CONTAINER_NO}}"),
        ("SEAL NO.: {{SEAL_NO}}", "SEAL NO.: {{SEAL_NO}}    DEST AGENT: {{DEST_AGENT_NAME}} {{DEST_AGENT_ADDR}} {{DEST_AGENT_TAX}} {{DEST_AGENT_TEL}}"),
    ])
    for row in ws.iter_rows():
        for cell in row:
            if cell.value in (8, 8.0) and cell.column == 3:
                cell.value = "{{PACKAGES}}"
            if cell.value in (7.92, 7.920) and cell.column == 4:
                cell.value = "{{VOLUME_CBM}}"
            if cell.value in (4000, 4000.0) and cell.column == 5:
                cell.value = "{{NET_KG}}"
            if cell.value in (4308, 4308.0) and cell.column == 6:
                cell.value = "{{GROSS_KG}}"
            if isinstance(cell.value, str) and cell.value.startswith("=SUM("):
                cell.value = cell.value  # 保留公式亦可；TOTAL 行由生成器写值
    wb.save(OUT / "SI-public.xlsx")
    print("SI <- PL shell")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    build_ci()
    build_pl()
    build_coa()
    build_si()
    for p in sorted(OUT.glob("*-public.xlsx")):
        print("wrote", p.name, p.stat().st_size)


if __name__ == "__main__":
    main()
