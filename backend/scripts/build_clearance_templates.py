# -*- coding: utf-8 -*-
"""按 MSDS 模板逻辑重做清关四单公共模板（成品版式 + {{占位符}}）。

对齐点：
1. MSDS `generate_msds_from_template`：成品 docx 模板 + `{{customs_name}}` 等占位
2. 订舱 `fill_booking_template`：xlsx 只读模板 + 字段替换，保留格式
3. 本脚本产出带边框/合并/列宽的 xlsx；填充由 `clearance_doc_service` 完成

运行: cd backend && python -m scripts.build_clearance_templates
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "references" / "clearance"

THIN = Side(style="thin", color="000000")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
RIGHT = Alignment(horizontal="right", vertical="center", wrap_text=True)
HEADER_FILL = PatternFill("solid", fgColor="D9E2F3")

FONT_CO = Font(name="Arial", size=12, bold=True)
FONT_TITLE = Font(name="Arial", size=14, bold=True)
FONT_H = Font(name="Arial", size=10, bold=True)
FONT = Font(name="Arial", size=10)


def _style_row(ws, row: int, cols: int, *, font=FONT, align=LEFT, border=True, fill=None):
    for c in range(1, cols + 1):
        cell = ws.cell(row, c)
        cell.font = font
        cell.alignment = align
        if border:
            cell.border = BOX
        if fill:
            cell.fill = fill


def _merge(ws, rng: str, value: str, *, font=FONT, align=CENTER, border=False):
    ws.merge_cells(rng)
    first = rng.split(":")[0]
    ws[first] = value
    ws[first].font = font
    ws[first].alignment = align
    if border:
        for row in ws[rng]:
            for cell in row:
                cell.border = BOX


def _letter_header(ws, cols: int, labels: list[str], row: int):
    for i, lab in enumerate(labels, 1):
        ws.cell(row, i, lab)
    _style_row(ws, row, cols, font=FONT_H, align=CENTER, fill=HEADER_FILL)
    ws.row_dimensions[row].height = 28


def _fill_ci(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "CI"
    for i, w in enumerate([6, 28, 14, 14, 14, 12], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    _merge(ws, "A1:F1", "{{COMPANY_NAME_EN}}", font=FONT_CO)
    _merge(ws, "A2:F2", "{{COMPANY_ADDR_EN}}", font=FONT, align=LEFT)
    _merge(ws, "A3:F3", "{{COMPANY_TEL_EN}}", font=FONT, align=LEFT)
    _merge(ws, "A5:F5", "TRANSPORT AND ROUTE：", font=FONT_H, align=LEFT)
    _merge(ws, "A6:F6", "{{ROUTE}}", font=FONT, align=LEFT)
    _merge(ws, "A7:C7", "CONTAINER NO.: {{CONTAINER_NO}}", font=FONT, align=LEFT)
    _merge(ws, "A8:C8", "SEAL NO.: {{SEAL_NO}}", font=FONT, align=LEFT)
    _merge(ws, "A10:F10", "COMMERCIAL INVOICE", font=FONT_TITLE)

    # 单头：TO / 发票号
    ws["A11"] = "TO:"
    ws["B11"] = "{{CONSIGNEE_NAME}}"
    ws["D11"] = "INVOICE NO.:"
    ws["E11"] = "{{INVOICE_NO}}"
    ws["B12"] = "{{CONSIGNEE_ADDR}} {{CONSIGNEE_TAX}}"
    ws["D12"] = "DATE:"
    ws["E12"] = "{{INVOICE_DATE}}"
    ws["D13"] = "PI NO.:"
    ws["E13"] = "{{PI_NO}}"
    ws["D14"] = "PRICE TERM:"
    ws["E14"] = "{{PRICE_TERM}}"
    for r in range(11, 15):
        _style_row(ws, r, 6)
    ws.merge_cells("B11:C11")
    ws.merge_cells("B12:C14")
    ws.merge_cells("E11:F11")
    ws.merge_cells("E12:F12")
    ws.merge_cells("E13:F13")
    ws.merge_cells("E14:F14")

    _letter_header(ws, 5, ["ITEM", "DESCRIPTION", "QUANTITY", "CIF PRICE", "AMOUNT"], 16)
    ws["C17"] = "(KGS)"
    ws["D17"] = "(USD)"
    ws["E17"] = "(USD)"
    _style_row(ws, 17, 5, align=CENTER)

    # 明细行（单产品；多产品后续可扩展）
    ws["A18"] = "1"
    ws["B18"] = "{{ITEM_DESC}}"
    ws["C18"] = "{{ITEM_QTY}}"
    ws["D18"] = "{{ITEM_PRICE}}"
    ws["E18"] = "{{ITEM_AMOUNT}}"
    _style_row(ws, 18, 5)

    ws["B19"] = "HS CODE: {{HS_CODES}}"
    ws["B20"] = "{{PO_LINE}}"
    ws["B21"] = "{{TOTALS_LINE}}"
    for r in range(19, 22):
        ws.merge_cells(f"B{r}:E{r}")
        _style_row(ws, r, 5, border=False)

    for i, r in enumerate(range(22, 28), 1):
        ws[f"A{r}"] = f"{{{{BANK_LINE{i}}}}}"
        ws.merge_cells(f"A{r}:F{r}")
        _style_row(ws, r, 6, border=False)

    ws["A28"] = "PAYMENT TERMS: {{PAYMENT_TERMS}}"
    ws.merge_cells("A28:F28")
    _style_row(ws, 28, 6, border=False)

    ws["A30"] = "TOTAL:"
    ws["B30"] = "{{TOTAL_QTY}}"
    ws["E30"] = "{{TOTAL_AMOUNT}}"
    _style_row(ws, 30, 5, font=FONT_H)
    ws.merge_cells("E30:F30")

    ws["A31"] = "{{AMOUNT_WORDS}}"
    ws.merge_cells("A31:F31")
    _style_row(ws, 31, 6, border=False)

    ws["E33"] = "{{COMPANY_NAME_EN}}"
    ws["E33"].alignment = RIGHT


def _fill_pl(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "PL"
    for i, w in enumerate([10, 32, 14, 14, 14, 14], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    _merge(ws, "A1:F1", "{{COMPANY_NAME_EN}}", font=FONT_CO)
    _merge(ws, "A2:F2", "{{COMPANY_ADDR_EN}}", font=FONT, align=LEFT)
    _merge(ws, "A3:F3", "{{COMPANY_TEL_EN}}", font=FONT, align=LEFT)
    _merge(ws, "A5:F5", "TRANSPORT AND ROUTE:", font=FONT_H, align=LEFT)
    _merge(ws, "A6:F6", "{{ROUTE}}", font=FONT, align=LEFT)
    _merge(ws, "A7:C7", "CONTAINER NO.: {{CONTAINER_NO}}", font=FONT, align=LEFT)
    _merge(ws, "A8:C8", "SEAL NO.: {{SEAL_NO}}", font=FONT, align=LEFT)
    _merge(ws, "A10:F10", "PACKING LIST", font=FONT_TITLE)

    ws["A11"] = "TO:"
    ws["B11"] = "{{CONSIGNEE_NAME}}"
    ws["D11"] = "PACKING NO.:"
    ws["E11"] = "{{PACKING_NO}}"
    ws["B12"] = "{{CONSIGNEE_ADDR}} {{CONSIGNEE_TAX}}"
    ws["D12"] = "DATE:"
    ws["E12"] = "{{INVOICE_DATE}}"
    ws["D13"] = "PI NO.:"
    ws["E13"] = "{{PI_NO}}"
    for r in range(11, 14):
        _style_row(ws, r, 6)
    ws.merge_cells("B11:C11")
    ws.merge_cells("B12:C14")
    ws.merge_cells("E11:F11")
    ws.merge_cells("E12:F12")
    ws.merge_cells("E13:F13")

    _letter_header(ws, 6, [
        "PACKING NO.", "DESCRIPTION", "PACKING QTY", "PACKING SIZE", "NET WEIGHT", "GROSS WEIGHT"
    ], 15)
    ws["C16"] = "(PALLETS)"
    ws["D16"] = "(CBM)"
    ws["E16"] = "(KGS)"
    ws["F16"] = "(KGS)"
    _style_row(ws, 16, 6, align=CENTER)

    ws["A17"] = "1"
    ws["B17"] = "{{ITEM_DESC}}"
    ws["C17"] = "{{PACKAGES}}"
    ws["D17"] = "{{VOLUME_CBM}}"
    ws["E17"] = "{{NET_KG}}"
    ws["F17"] = "{{GROSS_KG}}"
    _style_row(ws, 17, 6)

    ws["B18"] = "HS CODE: {{HS_CODES}}"
    ws["B19"] = "{{PO_LINE}}"
    ws["B20"] = "{{TOTALS_LINE}}"
    for r in range(18, 21):
        ws.merge_cells(f"B{r}:F{r}")
        _style_row(ws, r, 6, border=False)

    ws["A22"] = "TOTAL:"
    ws["C22"] = "{{PACKAGES}}"
    ws["D22"] = "{{VOLUME_CBM}}"
    ws["E22"] = "{{NET_KG}}"
    ws["F22"] = "{{GROSS_KG}}"
    _style_row(ws, 22, 6, font=FONT_H)

    ws["E24"] = "{{COMPANY_NAME_EN}}"
    ws["E24"].alignment = RIGHT


def _fill_coa(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "COA"
    for i, w in enumerate([22, 18, 24, 18], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    _merge(ws, "A1:D1", "{{COMPANY_NAME_EN}}", font=FONT_CO)
    _merge(ws, "A2:D2", "{{COMPANY_ADDR_EN}}", font=FONT, align=LEFT)
    _merge(ws, "A3:D3", "{{COMPANY_TEL_EN}}", font=FONT, align=LEFT)
    _merge(ws, "A6:D6", "CERTIFICATE OF ANALYSIS", font=FONT_TITLE)

    ws["A7"] = "PRODUCT NAME: {{PRODUCT_NAME}}"
    ws.merge_cells("A7:D7")
    ws["A8"] = "QUANTITY: {{SHIPPED_QTY}}"
    ws["C8"] = "BATCH NO.: {{BATCH_NO}}"
    ws["A9"] = "PRODUCTION DATE: {{PROD_DATE}}"
    ws["C9"] = "EXPIRATION DATE: {{EXP_DATE}}"
    ws.merge_cells("A8:B8")
    ws.merge_cells("C8:D8")
    ws.merge_cells("A9:B9")
    ws.merge_cells("C9:D9")
    for r in (7, 8, 9):
        _style_row(ws, r, 4, border=False)

    ws["A10"] = "PI No.: {{COA_PI_NO}}"
    ws.merge_cells("A10:D10")
    _style_row(ws, 10, 4, border=False)

    # 列：A 分类 | B 项目 | C 规格 SPECIFICATIONS | D 结果 RESULTS
    # 不可把 C/D 合并，否则规格/结果无法分别写入
    _letter_header(ws, 4, ["TESTS", "ITEM", "SPECIFICATIONS", "RESULTS"], 11)

    # 对齐样例：感官=外观；理化=含固量、pH（pH 属理化，勿放进感官）
    ws["A12"] = "SENSORY REQUIREMENTS"
    ws["B12"] = "APPEARANCE"
    ws["C12"] = "{{APPEARANCE_SPEC}}"
    ws["D12"] = "{{APPEARANCE_RESULT}}"
    ws.merge_cells("A12:A12")

    ws["A13"] = "PHYSICOCHEMICAL REQUIREMENT"
    ws["B13"] = "{{SOLID_LABEL}}"
    ws["C13"] = "{{SOLID_SPEC}}"
    ws["D13"] = "{{SOLID_RESULT}}"
    ws.merge_cells("A13:A14")

    ws["B14"] = "{{PH_LABEL}}"
    ws["C14"] = "{{PH_SPEC}}"
    ws["D14"] = "{{PH_RESULT}}"

    ws["B15"] = ""
    ws["C15"] = ""
    ws["D15"] = ""
    for r in range(12, 16):
        _style_row(ws, r, 4)

    ws["A16"] = "CONSEQUENCE"
    ws["B16"] = (
        "THE PRODUCT IS CONFORMED TO THESE STANDARD OF "
        "GB/T19001-2008 AND GB/T24001-2004."
    )
    ws.merge_cells("B16:D16")
    _style_row(ws, 16, 4, border=False)

    ws["A17"] = "MAKER: {{COMPANY_NAME_EN}}"
    ws.merge_cells("A17:D17")
    ws["A18"] = "THE CENTER OF QUALITY INSPECTION"
    ws.merge_cells("A18:D18")
    ws["A19"] = "{{COMPANY_NAME_EN}}"
    ws.merge_cells("A19:D19")
    for r in (17, 18, 19):
        _style_row(ws, r, 4, border=False, align=CENTER)


def _fill_si(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "SI"
    for i, w in enumerate([24, 36, 36], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    _merge(ws, "A1:C1", "BOOKING / SHIPPING INSTRUCTION (SI)", font=FONT_TITLE)
    _merge(ws, "A2:C2", "（订舱补料 — 非提单正本；正本由船公司签发）", font=FONT, align=LEFT)

    rows = [
        (4, "SHIPPER", "{{COMPANY_NAME_EN}}"),
        (5, "", "{{COMPANY_ADDR_EN}}"),
        (6, "CONSIGNEE", "{{CONSIGNEE_NAME}}"),
        (7, "", "{{CONSIGNEE_ADDR}}"),
        (8, "NOTIFY", "{{NOTIFY}}"),
        (9, "", "{{NOTIFY_ADDR}}"),
        (10, "DESTINATION AGENT", "{{DEST_AGENT_NAME}}"),
        (11, "", "{{DEST_AGENT_ADDR}}"),
        (12, "", "{{DEST_AGENT_TAX}} {{DEST_AGENT_TEL}}"),
        (14, "VESSEL / VOYAGE", "{{VESSEL}}"),
        (15, "B/L NO.", "{{BL_NO}}"),
        (16, "PORT OF LOADING", "{{LOADING_PORT}}"),
        (17, "PORT OF DISCHARGE", "{{DISCHARGE_PORT}}"),
        (18, "CONTAINER NO.", "{{CONTAINER_NO}}"),
        (19, "SEAL NO.", "{{SEAL_NO}}"),
        (21, "DESCRIPTION", "{{ITEM_DESC}}"),
        (22, "QTY / NET WEIGHT", "{{SHIPPED_QTY}}"),
        (23, "H.S. CODE", "{{HS_CODES}}"),
        (24, "PACKAGES", "{{TOTALS_LINE}}"),
        (25, "GROSS WEIGHT (KGS)", "{{GROSS_KG}}"),
        (26, "MEASUREMENT (CBM)", "{{VOLUME_CBM}}"),
        (27, "FREIGHT", "FREIGHT PREPAID"),
    ]
    for r, lab, val in rows:
        ws[f"A{r}"] = lab
        ws[f"B{r}"] = val
        ws.merge_cells(f"B{r}:C{r}")
        _style_row(ws, r, 3, border=True if lab else False)

    _merge(ws, "A29:C29", "{{COMPANY_NAME_EN}}", font=FONT_H, align=RIGHT)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    builders = {
        "CI-public.xlsx": _fill_ci,
        "PL-public.xlsx": _fill_pl,
        "COA-public.xlsx": _fill_coa,
        "SI-public.xlsx": _fill_si,
    }
    for name, fn in builders.items():
        wb = Workbook()
        fn(wb)
        path = OUT / name
        wb.save(path)
        print("wrote", path)


if __name__ == "__main__":
    main()
