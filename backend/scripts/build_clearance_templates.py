"""生成清关四单公共模板（脱敏、xlsx only）。

运行: cd backend && python -m scripts.build_clearance_templates
"""
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "references" / "clearance"


def _fill_ci(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "CI"
    rows = [
        ("{{COMPANY_NAME_EN}}",),
        ("{{COMPANY_ADDR_EN}}",),
        ("{{COMPANY_TEL_EN}}",),
        (),
        ("TRANSPORT AND ROUTE：",),
        ("{{ROUTE}}",),
        ("CONTAINER NO.: {{CONTAINER_NO}}",),
        ("SEAL NO.: {{SEAL_NO}}",),
        (),
        ("COMMERCIAL INVOICE",),
        ("TO:", "{{CONSIGNEE_NAME}}", "INVOICE NO.:", "{{INVOICE_NO}}"),
        ("", "{{CONSIGNEE_ADDR}} {{CONSIGNEE_TAX}}", "DATE:", "{{INVOICE_DATE}}"),
        ("", "", "PI NO.:", "{{PI_NO}}"),
        ("", "", "PRICE TERM:", "{{PRICE_TERM}}"),
        (),
        ("ITEM", "DESCRIPTION", "QUANTITY", "CIF PRICE", "AMOUNT"),
        ("", "", "(KGS)", "(USD)", "(USD)"),
        ("1", "{{ITEM_DESC}}", "{{ITEM_QTY}}", "{{ITEM_PRICE}}", "{{ITEM_AMOUNT}}"),
        ("", "HS CODE: {{HS_CODES}}",),
        ("", "{{PO_LINE}}",),
        ("", "{{TOTALS_LINE}}",),
        ("{{BANK_LINE1}}",),
        ("{{BANK_LINE2}}",),
        ("{{BANK_LINE3}}",),
        ("{{BANK_LINE4}}",),
        ("{{BANK_LINE5}}",),
        ("{{BANK_LINE6}}",),
        ("PAYMENT TERMS: {{PAYMENT_TERMS}}",),
        (),
        ("TOTAL:", "{{TOTAL_QTY}}", "", "", "{{TOTAL_AMOUNT}}"),
        ("{{AMOUNT_WORDS}}",),
        (),
        ("{{COMPANY_NAME_EN}}",),
    ]
    for r in rows:
        ws.append(list(r) if r else [None])


def _fill_pl(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "PL"
    rows = [
        ("{{COMPANY_NAME_EN}}",),
        ("{{COMPANY_ADDR_EN}}",),
        ("{{COMPANY_TEL_EN}}",),
        (),
        ("TRANSPORT AND ROUTE:",),
        ("{{ROUTE}}",),
        ("CONTAINER NO.: {{CONTAINER_NO}}",),
        ("SEAL NO.: {{SEAL_NO}}",),
        (),
        ("PACKING LIST",),
        ("TO:", "{{CONSIGNEE_NAME}}", "PACKING NO.:", "{{PACKING_NO}}"),
        ("", "{{CONSIGNEE_ADDR}} {{CONSIGNEE_TAX}}", "DATE:", "{{INVOICE_DATE}}"),
        ("", "", "PI NO.:", "{{PI_NO}}"),
        (),
        ("PACKING NO.", "DESCRIPTION", "PACKING QTY", "PACKING SIZE", "NET WEIGHT", "GROSS WEIGHT"),
        ("", "", "(PALLETS)", "(CBM)", "(KGS)", "(KGS)"),
        ("1", "{{ITEM_DESC}}", "{{PACKAGES}}", "{{VOLUME_CBM}}", "{{NET_KG}}", "{{GROSS_KG}}"),
        ("", "HS CODE: {{HS_CODES}}",),
        ("", "{{PO_LINE}}",),
        ("", "{{TOTALS_LINE}}",),
        (),
        ("TOTAL:", "{{PACKAGES}}", "{{VOLUME_CBM}}", "{{NET_KG}}", "{{GROSS_KG}}"),
        (),
        ("{{COMPANY_NAME_EN}}",),
    ]
    for r in rows:
        ws.append(list(r) if r else [None])


def _fill_coa(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "COA"
    rows = [
        ("{{COMPANY_NAME_EN}}",),
        ("{{COMPANY_ADDR_EN}}",),
        ("{{COMPANY_TEL_EN}}",),
        (),
        (),
        ("CERTIFICATE OF ANALYSIS",),
        ("PRODUCT NAME: {{PRODUCT_NAME}}",),
        ("QUANTITY: {{SHIPPED_QTY}}", "BATCH NO.: {{BATCH_NO}}"),
        ("PRODUCTION DATE: {{PROD_DATE}}", "EXPIRATION DATE: {{EXP_DATE}}"),
        ("PI No.: {{COA_PI_NO}}",),
        ("TESTS", "SPECIFICATIONS", "RESULTS"),
        ("SENSORY REQUIREMENTS", "APPEARANCE", "{{APPEARANCE_SPEC}}", "{{APPEARANCE_RESULT}}"),
        ("PHYSICOCHEMICAL REQUIREMENT", "{{SOLID_LABEL}}", "{{SOLID_SPEC}}", "{{SOLID_RESULT}}"),
        ("", "{{PH_LABEL}}", "{{PH_SPEC}}", "{{PH_RESULT}}"),
        ("CONSEQUENCE", "THE PRODUCT IS CONFORMED TO THESE STANDARD OF GB/T19001-2008 AND GB/T24001-2004."),
        ("MAKER: {{COMPANY_NAME_EN}}",),
        ("THE CENTER OF QUALITY INSPECTION",),
        ("{{COMPANY_NAME_EN}}",),
    ]
    for r in rows:
        ws.append(list(r) if r else [None])


def _fill_si(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "SI"
    rows = [
        ("BOOKING / SHIPPING INSTRUCTION (SI)",),
        ("（订舱补料 — 非提单正本；正本由船公司签发）",),
        (),
        ("SHIPPER", "{{COMPANY_NAME_EN}}", "{{COMPANY_ADDR_EN}}"),
        ("CONSIGNEE", "{{CONSIGNEE_NAME}}", "{{CONSIGNEE_ADDR}}"),
        ("NOTIFY", "{{NOTIFY}}", "{{NOTIFY_ADDR}}"),
        ("DESTINATION AGENT", "{{DEST_AGENT_NAME}}", "{{DEST_AGENT_ADDR}}"),
        ("", "{{DEST_AGENT_TAX}}", "{{DEST_AGENT_TEL}}"),
        (),
        ("VESSEL / VOYAGE", "{{VESSEL}}"),
        ("B/L NO.", "{{BL_NO}}"),
        ("PORT OF LOADING", "{{LOADING_PORT}}"),
        ("PORT OF DISCHARGE", "{{DISCHARGE_PORT}}"),
        ("CONTAINER NO.", "{{CONTAINER_NO}}"),
        ("SEAL NO.", "{{SEAL_NO}}"),
        (),
        ("DESCRIPTION", "{{ITEM_DESC}}"),
        ("QTY / NET WEIGHT", "{{SHIPPED_QTY}}"),
        ("H.S. CODE", "{{HS_CODES}}"),
        ("PACKAGES", "{{TOTALS_LINE}}"),
        ("GROSS WEIGHT (KGS)", "{{GROSS_KG}}"),
        ("MEASUREMENT (CBM)", "{{VOLUME_CBM}}"),
        ("FREIGHT", "FREIGHT PREPAID"),
    ]
    for r in rows:
        ws.append(list(r) if r else [None])


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
