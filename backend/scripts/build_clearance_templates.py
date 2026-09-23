# -*- coding: utf-8 -*-
"""从成品清关单副本生成公共模板：只替换动态字段为 {{占位符}}，保留原版式。

素材：
  CI/PL/COA: C:\\Users\\windows\\Desktop\\清关样例_已转xlsx\\
  SI（订舱补料）: references/clearance/samples_20260923/补料-WA254-fmt.xlsx
    —— 船务部确认的补料表单成品（WA254 JINTEX 票），非 PL 壳。

运行: cd backend && python -m scripts.build_clearance_templates
"""
from __future__ import annotations

import re
import shutil
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = Path(r"C:\Users\windows\Desktop\清关样例_已转xlsx")
NEW_SAMPLES = ROOT / "references" / "clearance" / "samples_20260923"
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


def _is_sample_date(value) -> bool:
    if isinstance(value, datetime):
        return value.date() == date(2026, 8, 1) or value.year == 2026 and value.month == 8 and value.day == 1
    if isinstance(value, date):
        return value == date(2026, 8, 1)
    if isinstance(value, str):
        return "2026-08-01" in value
    return False


def _replace_dates(ws):
    """样例日期可能是 datetime，不能只做字符串替换。"""
    for row in ws.iter_rows():
        for cell in row:
            if _is_sample_date(cell.value):
                cell.value = "{{INVOICE_DATE}}"
            elif isinstance(cell.value, str) and "2026-08-01" in cell.value:
                cell.value = cell.value.replace("2026-08-01", "{{INVOICE_DATE}}")


def _strip_stale_contacts(ws):
    """清掉 WA318 样例里写死的收货人 TEL/EMAIL（其它客户票会带上越南号码）。"""
    for row in ws.iter_rows():
        for cell in row:
            if not isinstance(cell.value, str):
                continue
            s = cell.value
            s = re.sub(r"\n?TEL: \+84 987 208 205", "", s)
            s = re.sub(r"\n?EMAIL: THUY\.PHAM@CHEMZONEVN\.COM", "", s)
            s = re.sub(r"\n{3,}", "\n", s)
            if s != cell.value:
                cell.value = s.strip("\n")


def _replace_bank_block(ws):
    for row in ws.iter_rows():
        for cell in row:
            if not isinstance(cell.value, str):
                continue
            t = cell.value.upper()
            if "BENEFICIARY BANK :" in t or "BENEFICIARY BANK:" in t:
                cell.value = "{{BANK_LINE1}}"
            elif ("BANK ADDRESS" in t and "BENEFICIARY" in t) or t.startswith("BEBEFICIARY BANK ADDRESS"):
                cell.value = "{{BANK_LINE2}}"
            elif "BENEFICIARY NAME" in t:
                cell.value = "{{BANK_LINE3}}"
            elif "COMPANY ADDRESS" in t and "BENEFICIARY" in t:
                cell.value = "{{BANK_LINE4}}"
            elif "BANK A/C" in t or "BANK AC" in t:
                cell.value = "{{BANK_LINE5}}"
            elif "SWIFT" in t:
                cell.value = "{{BANK_LINE6}}"


def _replace_formulas(ws, kind: str = "ci"):
    """公式格 → 占位符。CI 合计是数量/金额；PL 合计是件数/体积/净/毛。"""
    mapping = {
        "ci": {
            "=SUM(C": "{{TOTAL_QTY}}",
            "=SUM(E": "{{TOTAL_AMOUNT}}",
            "=C": "{{ITEM_AMOUNT}}",
        },
        "pl": {
            "=SUM(C": "{{PACKAGES}}",
            "=SUM(D": "{{VOLUME_CBM}}",
            "=SUM(E": "{{NET_KG}}",
            "=SUM(F": "{{GROSS_KG}}",
        },
    }.get(kind, {})
    for row in ws.iter_rows():
        for cell in row:
            if not isinstance(cell.value, str) or not cell.value.startswith("="):
                continue
            if "SUM" in cell.value:
                for prefix, ph in mapping.items():
                    if prefix.startswith("=SUM") and cell.value.startswith(prefix):
                        cell.value = ph
                        break
            elif kind == "ci" and cell.value.startswith("=C"):
                cell.value = "{{ITEM_AMOUNT}}"


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
    _strip_stale_contacts(ws)
    _replace_bank_block(ws)
    _replace_dates(ws)
    for row in ws.iter_rows():
        for cell in row:
            if cell.value in (4000, 4000.0) and cell.column == 3:
                cell.value = "{{ITEM_QTY}}" if cell.row < 25 else "{{TOTAL_QTY}}"
            if cell.value in (2.6, 2.60) and cell.column == 4:
                cell.value = "{{ITEM_PRICE}}"
            if cell.value in (10400, 10400.0) and cell.column in (5, 6):
                cell.value = "{{ITEM_AMOUNT}}" if cell.row < 25 else "{{TOTAL_AMOUNT}}"
    _replace_formulas(ws, "ci")
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
    _strip_stale_contacts(ws)
    _replace_dates(ws)
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value in ("1-8", "1-{{PACKAGES}}"):
                cell.value = "{{PACKING_RANGE}}"
            if cell.value in (8, 8.0) and cell.column == 3:
                cell.value = "{{PACKAGES}}"
            if cell.value in (7.92, 7.920) and cell.column == 4:
                cell.value = "{{VOLUME_CBM}}"
            if cell.value in (4000, 4000.0) and cell.column == 5:
                cell.value = "{{NET_KG}}"
            if cell.value in (4308, 4308.0) and cell.column == 6:
                cell.value = "{{GROSS_KG}}"
    _replace_formulas(ws, "pl")
    wb.save(OUT / "PL-public.xlsx")
    print("PL <-", src.name)


def build_coa():
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
    for row in ws.iter_rows():
        for cell in row:
            if cell.value in (32.39, "32.39"):
                cell.value = "{{SOLID_RESULT}}"
            elif cell.value in (3.79, "3.79"):
                cell.value = "{{PH_RESULT}}"
            if isinstance(cell.value, str) and "Slight odour" in cell.value and cell.column >= 5:
                cell.value = "{{ODOUR_RESULT}}"
    seen = 0
    for row in ws.iter_rows():
        for cell in row:
            if cell.value == "{{APPEARANCE_SPEC}}":
                seen += 1
                if seen == 2:
                    cell.value = "{{APPEARANCE_RESULT}}"
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
    has_pi = any(
        isinstance(c.value, str) and "{{COA_PI_NO}}" in c.value
        for row in ws.iter_rows()
        for c in row
    )
    if not has_pi:
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
    """SI = 船务部补料表单（成品副本 + 占位符）。

    源：WA254 票补料成品（单货描多行单元格版式）。
    货描区用 {{SI_DESC_BLOCK}} 整块替换 —— 单品/多品都由生成器拼文本，
    避免在表单合并单元格里做行扩。
    """
    src = NEW_SAMPLES / "补料-WA254-fmt.xlsx"
    if not src.exists():
        # 回退：附件补料（BLUETEC 10 品版式，同样支持）
        src = NEW_SAMPLES / "补料-fmt.xlsx"
    shutil.copy2(src, OUT / "SI-public.xlsx")
    wb = load_workbook(OUT / "SI-public.xlsx")
    ws = wb.worksheets[0]
    ws.title = "SI"

    # 标题
    ws["A1"] = "补料"

    # 收货人块（WA254 三行：名称/地址/联系）
    _patch_text(ws, [
        ("JINTEX CORPORATION LTD.", "{{CONSIGNEE_NAME}}"),
        ("12F,\xa0NO.\xa0126,NANKING\xa0EAST\xa0ROAD,\xa0SEC.4, TAIPEI,10595\xa0TAIWAN", "{{CONSIGNEE_ADDR}}"),
        ("12F, NO. 126,NANKING EAST ROAD, SEC.4, TAIPEI,10595 TAIWAN", "{{CONSIGNEE_ADDR}}"),
        ("TEL: +886-3-386-9968  EXT.425\nE-MAIL:RITA.HO@JINTEX-CHEMICAL.COM", "{{CONSIGNEE_TAX}}"),
        ("SAME AS CONSIGNEE", "{{NOTIFY}}"),
        ("KEELUNG", "{{DISCHARGE_PORT}}"),
        ("NANSHA,CHINA", "{{LOADING_PORT}}"),
        ("NANSHA, CHINA", "{{LOADING_PORT}}"),
        ("FIXING AGENT HT-900P\nNET WEIGHT:360KGS\nH.S.CODE:3809.9190\nTOTAL: 3 DRUMS PACKED ON 1 PALLET", "{{SI_DESC_BLOCK}}"),
        ("HT-900P", "{{MARKS}}"),
        ("备注：出电放提单/需要买保险，电子保单,被保险人是收货人", "{{REMARK}}"),
        ("沛華運通國際物流（中國）有限公司廣州分公司", "{{DEST_AGENT_NAME}}"),
        ("PACIFIC STAR EXPRESS (CHINA) CO.,LTD.", "{{DEST_AGENT_ADDR}}"),
        ("GUANGZHOU BRANCH", "{{DEST_AGENT_TAX}}"),
    ])

    # Final Destination 与卸货港同值（样例 KEELUNG/KEELUNG）——第二处 KEELUNG 已被上一步
    # 先扫一遍把残留 KEELUNG（Final Destination 列）也替换掉
    for row in ws.iter_rows():
        for cell in row:
            if cell.value in ("KEELUNG", "{{DISCHARGE_PORT}}") and cell.column == 4:
                cell.value = "{{FINAL_DEST}}"
            if cell.value == "{{DISCHARGE_PORT}}" and cell.column == 4:
                cell.value = "{{FINAL_DEST}}"

    # 船名航次 / 提单号 / 箱号数量
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and "Vessel/Voy" in cell.value:
                # 标签行；值写在同行右侧或下一空格 —— 统一写在 B 列
                ws.cell(cell.row, 2).value = "{{VESSEL}}"
            if isinstance(cell.value, str) and "B/L NO" in cell.value:
                ws.cell(cell.row, 8).value = "{{BL_NO}}"

    # 货描 / 包装数字格
    for row in ws.iter_rows():
        for cell in row:
            if cell.value == 1 and cell.column == 7 and cell.row < 35:
                cell.value = "{{PACKAGES}}"
            if cell.value == 1.0 and cell.column == 7 and cell.row < 35:
                cell.value = "{{PACKAGES}}"
            if cell.value in (407, 407.0) and cell.column == 9:
                cell.value = "{{GROSS_KG}}"
            if cell.value in (0.95, 0.950) and cell.column == 11:
                cell.value = "{{VOLUME_CBM}}"
            if isinstance(cell.value, str) and cell.value.strip() in ("PALLET", "DRUMS", "BAGS"):
                cell.value = "{{PACKAGE_UNIT}}"

    # 箱型数量（20'GP 前的数字）
    for row in ws.iter_rows():
        for cell in row:
            if cell.value in (1, 1.0) and cell.column == 7 and 15 <= cell.row <= 25:
                cell.value = "{{CONTAINER_QTY}}"

    wb.save(OUT / "SI-public.xlsx")
    print("SI <-", src.name, "(补料表单)")


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
