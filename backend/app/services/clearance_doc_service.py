# -*- coding: utf-8 -*-
"""清关四单生成：加载客户/公共模板 → 填占位符 → xlsx bytes。

对齐 MSDS generate_msds_from_template：
- 「标签：{{KEY}}」混排子串替换，保留样式
- 优先 customer_templates（一客一模板），否则公共模板
- overrides.extra_notes 追加说明行
"""
from __future__ import annotations

import base64
import re
import time
from io import BytesIO
from typing import Any, Dict, Optional, Tuple, Union

import openpyxl
from openpyxl.styles import Alignment

from app.schemas.ledger import LedgerRecordResponse
from app.services.clearance_fields import build_clearance_payload
from app.services import template_service

_DOC_TYPES = ("ci", "pl", "coa", "si")
_PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}")


def _fmt(value: Any) -> str:
    return "" if value is None else str(value)


def _build_mapping(payload: Dict[str, Any]) -> Dict[str, str]:
    items = payload.get("items") or []
    first = items[0] if items else {}
    po_no = payload.get("po_no") or ""
    po_line = f"PO#{po_no}" if payload.get("show_po") and po_no else ""
    packages_display = (
        payload.get("pallets") if payload.get("pallets") is not None else payload.get("packages", "")
    )
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


def _append_extra_notes(wb, extra_notes) -> None:
    if not extra_notes:
        return
    notes = [str(n).strip() for n in extra_notes if n and str(n).strip()]
    if not notes:
        return
    ws = wb.worksheets[0]
    start = (ws.max_row or 1) + 2
    for i, note in enumerate(notes):
        c = ws.cell(start + i, 1, note)
        c.alignment = Alignment(wrap_text=True, vertical="center")


class ClearanceDocService:
    def load_template(
        self, doc_type: str, customer_code: Optional[str] = None
    ) -> openpyxl.Workbook:
        if doc_type not in _DOC_TYPES:
            raise ValueError(f"Unknown clearance doc_type: {doc_type}")
        blob, _src = template_service.load_template_bytes(customer_code, doc_type)
        return openpyxl.load_workbook(BytesIO(blob))

    def generate(
        self,
        doc_type: str,
        record: LedgerRecordResponse,
        company_code: Optional[str] = None,
        overrides: Optional[Union[Dict[str, Any], Any]] = None,
        customer_code: Optional[str] = None,
    ) -> Tuple[bytes, str, str]:
        """返回 (xlsx_bytes, doc_key, b64)。"""
        if doc_type not in _DOC_TYPES:
            raise ValueError(f"Unknown clearance doc_type: {doc_type}")
        if isinstance(overrides, dict):
            ov = overrides
        elif overrides is None:
            ov = {}
        else:
            ov = dict(overrides)

        cust = customer_code or ov.get("customer_code") or getattr(record, "customer_code", None)
        payload = build_clearance_payload(record, company_code, ov)
        mapping = _build_mapping(payload)
        wb = self.load_template(doc_type, customer_code=cust)
        _fill_workbook(wb, mapping)
        _append_extra_notes(wb, ov.get("extra_notes"))
        buf = BytesIO()
        wb.save(buf)
        content = buf.getvalue()
        doc_key = f"{doc_type}_{int(time.time())}"
        return content, doc_key, base64.b64encode(content).decode()
