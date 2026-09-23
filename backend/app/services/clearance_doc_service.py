# -*- coding: utf-8 -*-
"""清关四单：读公共模板 → 填占位符（MSDS 风格）→ 返回 xlsx bytes。

对齐 MSDS `generate_msds_from_template` + `_fill_placeholder`：
- 可在「标签：{{KEY}}」整串中做子串替换，保留前后文
- 只改单元格值，不破坏 openpyxl 样式（边框/合并/字体）
- 模板只读加载；未提供值的占位符替换为空（可标黄由 UI 层处理）

与订舱 `fill_booking_template` 的差异：
- 订舱走 zip XML 以保留 shapes；清关模板由脚本生成、无 shapes，
  openpyxl 足够，且要支持「标签+占位」混排。
"""
from __future__ import annotations

import base64
import re
import time
from io import BytesIO
from typing import Any, Optional

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

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def _item_aliases(payload: dict[str, Any]) -> dict[str, Any]:
    """明细别名：ITEM_DESC / ITEM_QTY ... 取第一行（MVP 单产品）。"""
    alias: dict[str, Any] = {}
    items = payload.get("items") or []
    if items:
        it = items[0]
        alias["ITEM_DESC"] = it.get("desc") or ""
        alias["ITEM_QTY"] = it.get("qty") if it.get("qty") is not None else ""
        alias["ITEM_PRICE"] = it.get("price") if it.get("price") is not None else ""
        alias["ITEM_AMOUNT"] = it.get("amount") if it.get("amount") is not None else ""
    else:
        alias.update({"ITEM_DESC": "", "ITEM_QTY": "", "ITEM_PRICE": "", "ITEM_AMOUNT": ""})
    alias["PO_LINE"] = f"PO#{payload['po_no']}" if payload.get("show_po") and payload.get("po_no") else ""
    alias["VOLUME_CBM"] = payload.get("volume_cbm", "")
    alias["NET_KG"] = payload.get("net_kg", "")
    alias["GROSS_KG"] = payload.get("gross_kg", "")
    # PL 的 PACKAGES 列：样例 WA318=托、WA254=桶；默认托
    alias["PACKAGES"] = payload.get("pallets") if payload.get("pallets") is not None else payload.get("packages", "")
    alias["SHIPPED_QTY"] = payload.get("shipped_qty_text", "")
    alias["PRODUCT_NAME"] = payload.get("product_name", "")
    alias["DISCHARGE_PORT"] = payload.get("discharge_port", "")
    alias["LOADING_PORT"] = payload.get("loading_port", "")
    alias["VESSEL"] = payload.get("vessel", "")
    alias["BL_NO"] = payload.get("bl_no", "")
    for key in (
        "DEST_AGENT_NAME",
        "DEST_AGENT_ADDR",
        "DEST_AGENT_TAX",
        "DEST_AGENT_TEL",
        "BANK_LINE1",
        "BANK_LINE2",
        "BANK_LINE3",
        "BANK_LINE4",
        "BANK_LINE5",
        "BANK_LINE6",
    ):
        alias[key] = payload.get(key.lower(), "")
    return alias


def fill_workbook(wb: openpyxl.Workbook, payload: dict[str, Any]) -> None:
    """MSDS 式填充：支持整格 {{KEY}} 与「标签：{{KEY}}」混排。"""
    mapping: dict[str, Any] = {k.upper(): v for k, v in payload.items() if not isinstance(v, (list, dict))}
    mapping.update({k.upper(): v for k, v in _item_aliases(payload).items()})

    def _sub(text: str) -> str:
        def repl(m: re.Match) -> str:
            key = m.group(1).upper()
            val = mapping.get(key, "")
            return "" if val is None else str(val)

        out = _PLACEHOLDER_RE.sub(repl, text)
        # 清掉未映射残留
        return _PLACEHOLDER_RE.sub("", out)

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and "{{" in cell.value:
                    cell.value = _sub(cell.value)


class ClearanceDocService:
    def load_template(self, doc_type: str) -> openpyxl.Workbook:
        key = _DOC_TYPE_TO_TEMPLATE.get(doc_type)
        if not key:
            raise ValueError(f"Unknown clearance doc_type: {doc_type}")
        path = TEMPLATES[key]
        return openpyxl.load_workbook(path)

    def generate(
        self,
        doc_type: str,
        record: LedgerRecordResponse,
        company_code: Optional[str] = None,
        overrides: Optional[dict] = None,
    ) -> tuple[bytes, str, str]:
        """返回 (xlsx_bytes, doc_key, b64)。"""
        payload = build_clearance_payload(record, company_code, overrides or {})
        wb = self.load_template(doc_type)
        fill_workbook(wb, payload)
        buf = BytesIO()
        wb.save(buf)
        content = buf.getvalue()
        doc_key = f"{doc_type}_{int(time.time())}"
        return content, doc_key, base64.b64encode(content).decode()
