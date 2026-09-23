"""清关四单生成：用 payload 填充 public 模板占位符。"""
import base64
import re
import time
from io import BytesIO
from typing import Any, Dict, Optional, Tuple, Union

import openpyxl

from app.core.config import TEMPLATES
from app.schemas.ledger import LedgerRecordResponse
from app.services.clearance_fields import build_clearance_payload

_DOC_TYPE_TO_TEMPLATE = {
    "ci": "clearance_ci",
    "pl": "clearance_pl",
    "coa": "clearance_coa",
    "si": "clearance_si",
}

_PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}")


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _build_mapping(payload: Dict[str, Any]) -> Dict[str, str]:
    items = payload.get("items") or []
    first = items[0] if items else {}
    po_no = payload.get("po_no") or ""
    show_po = payload.get("show_po")
    po_line = f"PO#{po_no}" if show_po and po_no else ""
    pallets = payload.get("pallets")
    packages = payload.get("packages")
    packages_display = pallets if pallets is not None else packages

    raw = {
        "COMPANY_NAME_EN": payload.get("company_name_en", ""),
        "COMPANY_ADDR_EN": payload.get("company_addr_en", ""),
        "COMPANY_TEL_EN": payload.get("company_tel_en", ""),
        "CONSIGNEE_NAME": payload.get("consignee_name", ""),
        "CONSIGNEE_ADDR": payload.get("consignee_addr", ""),
        "CONSIGNEE_TAX": payload.get("consignee_tax", ""),
        "NOTIFY": payload.get("notify", ""),
        "NOTIFY_ADDR": payload.get("notify_addr", ""),
        "DEST_AGENT_NAME": payload.get("dest_agent_name", ""),
        "DEST_AGENT_ADDR": payload.get("dest_agent_addr", ""),
        "DEST_AGENT_TAX": payload.get("dest_agent_tax", ""),
        "DEST_AGENT_TEL": payload.get("dest_agent_tel", ""),
        "INVOICE_NO": payload.get("invoice_no", ""),
        "PACKING_NO": payload.get("packing_no", ""),
        "PI_NO": payload.get("pi_no", ""),
        "INVOICE_DATE": payload.get("invoice_date", ""),
        "PRICE_TERM": payload.get("price_term", ""),
        "PAYMENT_TERMS": payload.get("payment_terms", ""),
        "ROUTE": payload.get("route", ""),
        "LOADING_PORT": payload.get("loading_port", ""),
        "DISCHARGE_PORT": payload.get("discharge_port", ""),
        "VESSEL": payload.get("vessel", ""),
        "BL_NO": payload.get("bl_no", ""),
        "CONTAINER_NO": payload.get("container_no", ""),
        "SEAL_NO": payload.get("seal_no", ""),
        "ITEM_DESC": first.get("desc", ""),
        "ITEM_QTY": first.get("qty", ""),
        "ITEM_PRICE": first.get("price", ""),
        "ITEM_AMOUNT": first.get("amount", ""),
        "HS_CODES": payload.get("hs_codes", ""),
        "PO_LINE": po_line,
        "TOTALS_LINE": payload.get("totals_line", ""),
        "TOTAL_QTY": payload.get("total_qty", ""),
        "TOTAL_AMOUNT": payload.get("total_amount", ""),
        "AMOUNT_WORDS": payload.get("amount_words", ""),
        "PACKAGES": packages_display,
        "VOLUME_CBM": payload.get("volume_cbm", ""),
        "NET_KG": payload.get("net_kg", ""),
        "GROSS_KG": payload.get("gross_kg", ""),
        "PRODUCT_NAME": payload.get("product_name", ""),
        "SHIPPED_QTY": payload.get("shipped_qty_text", ""),
        "BATCH_NO": payload.get("batch_no", ""),
        "PROD_DATE": payload.get("prod_date", ""),
        "EXP_DATE": payload.get("exp_date", ""),
        "COA_PI_NO": payload.get("coa_pi_no", ""),
        "PH_LABEL": payload.get("ph_label", ""),
        "PH_SPEC": payload.get("ph_spec", ""),
        "PH_RESULT": payload.get("ph_result", ""),
        "SOLID_LABEL": payload.get("solid_label", ""),
        "SOLID_SPEC": payload.get("solid_spec", ""),
        "SOLID_RESULT": payload.get("solid_result", ""),
        "APPEARANCE_SPEC": payload.get("appearance_spec", ""),
        "APPEARANCE_RESULT": payload.get("appearance_result", ""),
        "BANK_LINE1": payload.get("bank_line1", ""),
        "BANK_LINE2": payload.get("bank_line2", ""),
        "BANK_LINE3": payload.get("bank_line3", ""),
        "BANK_LINE4": payload.get("bank_line4", ""),
        "BANK_LINE5": payload.get("bank_line5", ""),
        "BANK_LINE6": payload.get("bank_line6", ""),
    }
    return {k: _fmt(v) for k, v in raw.items()}


def _fill_workbook(wb, mapping: Dict[str, str]) -> None:
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue
                text = str(cell.value)
                if "{{" not in text:
                    continue
                for key, val in mapping.items():
                    text = text.replace("{{" + key + "}}", val)
                text = _PLACEHOLDER_RE.sub("", text)
                cell.value = text


class ClearanceDocService:
    """加载 public 模板并填充 {{PLACEHOLDER}}，生成清关四单。"""

    def generate(
        self,
        doc_type: str,
        record: LedgerRecordResponse,
        company_code: Optional[str] = None,
        overrides: Optional[Union[Dict[str, Any], Any]] = None,
    ) -> Tuple[bytes, str, str]:
        template_key = _DOC_TYPE_TO_TEMPLATE.get(doc_type)
        if template_key is None:
            raise ValueError(f"Unknown clearance doc_type: {doc_type}")
        template_path = TEMPLATES[template_key]
        payload = build_clearance_payload(record, company_code, overrides or {})
        mapping = _build_mapping(payload)
        wb = openpyxl.load_workbook(template_path)
        _fill_workbook(wb, mapping)
        buf = BytesIO()
        wb.save(buf)
        content = buf.getvalue()
        doc_key = f"{doc_type}_{int(time.time())}"
        return content, doc_key, base64.b64encode(content).decode()
