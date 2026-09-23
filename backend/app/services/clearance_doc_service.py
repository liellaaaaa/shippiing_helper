# -*- coding: utf-8 -*-
"""清关四单生成：加载客户/公共模板 → 填占位符 → xlsx bytes。

对齐 MSDS generate_msds_from_template：
- 「标签：{{KEY}}」混排子串替换，保留样式
- 优先 customer_templates（一客一模板），否则公共模板
- overrides.extra_notes 追加说明行
"""
from __future__ import annotations

import base64
import copy
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


def _extract_batch_test_fields(batch: Dict[str, Any]) -> Dict[str, str]:
    """从批次 tests[] /扁平字段提取 COA 检测项（报告写什么就填什么）。

    tests[] 形状：{key, name_cn, label_en, spec, result}
    扁平字段（appearance_spec / ph_label / …）优先于 tests[]（前端可编辑覆盖）。
    """
    out: Dict[str, str] = {
        "appearance_spec": "",
        "appearance_result": "",
        "ph_label": "",
        "ph_spec": "",
        "ph_result": "",
        "solid_label": "",
        "solid_spec": "",
        "solid_result": "",
        "odour_label": "",
        "odour_spec": "",
        "odour_result": "",
    }
    for t in batch.get("tests") or []:
        if not isinstance(t, dict):
            continue
        key = (t.get("key") or "").strip().lower()
        spec = t.get("spec") or ""
        result = t.get("result") or ""
        label = t.get("label_en") or ""
        if key == "appearance":
            # 外观规格全文保留（含「久置变深」等修饰语）
            out["appearance_spec"] = spec
            out["appearance_result"] = result
        elif key == "ph":
            out["ph_label"] = label or out["ph_label"]
            out["ph_spec"] = spec
            out["ph_result"] = result
        elif key == "solid":
            out["solid_label"] = label or out["solid_label"]
            out["solid_spec"] = spec
            out["solid_result"] = result
        elif key == "odour":
            out["odour_label"] = label or out["odour_label"]
            out["odour_spec"] = spec
            out["odour_result"] = result
    # 前端编辑后的扁平字段覆盖 tests[] 提取值
    for k in out:
        flat = batch.get(k)
        if flat not in (None, ""):
            out[k] = str(flat)
    return out


def _build_mapping(payload: Dict[str, Any]) -> Dict[str, str]:
    items = payload.get("items") or []
    first = items[0] if items else {}
    po_no = payload.get("po_no") or ""
    po_line = f"PO#{po_no}" if payload.get("show_po") and po_no else ""
    packages_display = payload.get("packages_display")
    if packages_display is None:
        packages_display = (
            payload.get("pallets") if payload.get("pallets") is not None else payload.get("packages", "")
        )
    raw: Dict[str, Any] = {
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
        "ITEM_COUNT": len(items),
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
        "ODOUR_LABEL": payload.get("odour_label", ""),
        "ODOUR_SPEC": payload.get("odour_spec", ""),
        "ODOUR_RESULT": payload.get("odour_result", ""),
        "BANK_LINE1": payload.get("bank_line1", ""),
        "BANK_LINE2": payload.get("bank_line2", ""),
        "BANK_LINE3": payload.get("bank_line3", ""),
        "BANK_LINE4": payload.get("bank_line4", ""),
        "BANK_LINE5": payload.get("bank_line5", ""),
        "BANK_LINE6": payload.get("bank_line6", ""),
    }
    # Multi-item rows: ITEM_*_1..N (legacy ITEM_* stay as aliases of item 1)
    for idx, it in enumerate(items, 1):
        raw[f"ITEM_NO_{idx}"] = it.get("index", idx)
        raw[f"ITEM_DESC_{idx}"] = it.get("desc", "")
        raw[f"ITEM_QTY_{idx}"] = it.get("qty", "")
        raw[f"ITEM_PRICE_{idx}"] = it.get("price", "")
        raw[f"ITEM_AMOUNT_{idx}"] = it.get("amount", "")
        raw[f"ITEM_HS_{idx}"] = it.get("hs_code", "")
        raw[f"ITEM_PACKAGES_{idx}"] = it.get("packages_display", it.get("drums", ""))
        raw[f"ITEM_CBM_{idx}"] = it.get("cbm", "")
        raw[f"ITEM_NET_{idx}"] = it.get("net_kg", "")
        raw[f"ITEM_GROSS_{idx}"] = it.get("gross_kg", "")
    return {k: _fmt(v) for k, v in raw.items()}


def _fill_workbook_on_sheet(ws, mapping: Dict[str, str]) -> None:
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


def _fill_workbook(wb, mapping: Dict[str, str]) -> None:
    for ws in wb.worksheets:
        _fill_workbook_on_sheet(ws, mapping)


def _unmerge_from_row(ws, from_row: int) -> list:
    """Unmerge ranges starting at from_row; return (min_col, min_row, max_col, max_row) list."""
    moves = []
    for mr in list(ws.merged_cells.ranges):
        if mr.min_row >= from_row:
            moves.append((mr.min_col, mr.min_row, mr.max_col, mr.max_row))
            ws.unmerge_cells(str(mr))
    return moves


def _apply_merged_ranges(ws, moves: list, n: int) -> None:
    for min_col, min_row, max_col, max_row in moves:
        ws.merge_cells(
            start_row=min_row + n,
            start_column=min_col,
            end_row=max_row + n,
            end_column=max_col,
        )


def _find_row_containing(ws, token: str) -> Optional[int]:
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is not None and token in str(cell.value):
                return cell.row
    return None


def _expand_ci_detail_rows(ws, n_items: int, payload: Dict[str, Any]) -> None:
    """CI 多产品：把 1 行明细扩成 N 行，并重写 TOTAL 汇总（避免 SUM 范围过期）。"""
    if n_items <= 1:
        return
    detail_row = _find_row_containing(ws, "{{ITEM_DESC}}")
    if detail_row is None:
        detail_row = _find_row_containing(ws, "{{ITEM_DESC_1}}") or 18

    n_new = n_items - 1
    merges = _unmerge_from_row(ws, detail_row + 1)
    ws.insert_rows(detail_row + 1, n_new)
    _apply_merged_ranges(ws, merges, n_new)

    src_height = ws.row_dimensions[detail_row].height
    for i in range(n_items):
        row = detail_row + i
        if i > 0:
            if src_height:
                ws.row_dimensions[row].height = src_height
            for col in range(1, 7):
                src_cell = ws.cell(detail_row, col)
                dst_cell = ws.cell(row, col)
                dst_cell._style = copy.copy(src_cell._style)
        idx = i + 1
        ws.cell(row, 1).value = str(idx)
        ws.cell(row, 2).value = f"{{{{ITEM_DESC_{idx}}}}}"
        ws.cell(row, 3).value = f"{{{{ITEM_QTY_{idx}}}}}"
        ws.cell(row, 4).value = f"{{{{ITEM_PRICE_{idx}}}}}"
        ws.cell(row, 5).value = f"{{{{ITEM_AMOUNT_{idx}}}}}"

    # TOTAL 行：写值汇总全部明细（覆盖全量 item 行，避免 SUM 范围过期）
    total_row = _find_row_containing(ws, "{{TOTAL_QTY}}")
    if total_row is None:
        total_row = _find_row_containing(ws, "TOTAL:")
    if total_row is not None:
        _set_cell_value(ws, total_row, 2, payload.get("total_qty", 0))
        _set_cell_value(ws, total_row, 5, payload.get("total_amount", 0))


def _set_cell_value(ws, row: int, col: int, value: Any) -> None:
    """Write to the anchor cell if (row, col) falls inside a merge."""
    cell = ws.cell(row, col)
    if cell.__class__.__name__ == "MergedCell":
        for mr in ws.merged_cells.ranges:
            if mr.min_row <= row <= mr.max_row and mr.min_col <= col <= mr.max_col:
                ws.cell(mr.min_row, mr.min_col).value = value
                return
    cell.value = value


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
        wb = self.load_template(doc_type, customer_code=cust)

        # COA 多批次：一批一 sheet（录音：不同批次出货放同一 COA 不同 sheet）
        batches = ov.get("batches") or []
        if doc_type == "coa" and isinstance(batches, list) and len(batches) >= 1:
            self._fill_coa_batches(wb, payload, batches)
        else:
            items = payload.get("items") or []
            if doc_type == "ci" and len(items) > 1:
                _expand_ci_detail_rows(wb.worksheets[0], len(items), payload)
            mapping = _build_mapping(payload)
            _fill_workbook(wb, mapping)
            _append_extra_notes(wb, ov.get("extra_notes"))

        buf = BytesIO()
        wb.save(buf)
        content = buf.getvalue()
        doc_key = f"{doc_type}_{int(time.time())}"
        return content, doc_key, base64.b64encode(content).decode()

    def _fill_coa_batches(self, wb, base_payload: dict, batches: list) -> None:
        """用检测报告批次填充 COA；多批时一批一 sheet。PI 固定本票。"""
        template_ws = wb.worksheets[0]
        # 清空多余 sheet，按批次数复制干净模板（先复制再填，避免拷到已替换占位符的 sheet）
        while len(wb.worksheets) > 1:
            wb.remove(wb.worksheets[1])
        sheets = [template_ws]
        for _ in range(1, len(batches)):
            sheets.append(wb.copy_worksheet(template_ws))

        for i, batch in enumerate(batches):
            ws = sheets[i]
            ws.title = str(batch.get("batch_no") or f"COA-{i + 1}")[:31]
            fields = _extract_batch_test_fields(batch)

            p = dict(base_payload)
            p["batch_no"] = batch.get("batch_no") or p.get("batch_no") or ""
            if batch.get("quantity_text"):
                p["shipped_qty_text"] = batch["quantity_text"]
            # PROD_DATE：批次自带 → 批号推导；多批不继承单批基线日期
            prod = batch.get("prod_date") or ""
            if not prod and p["batch_no"]:
                from app.services.coa_date_service import parse_production_date_from_batch

                pd = parse_production_date_from_batch(p["batch_no"])
                if pd:
                    prod = pd.isoformat()
            p["prod_date"] = prod
            # 检测项：报告写什么就填什么（含外观「久置变深」）
            p["appearance_spec"] = fields.get("appearance_spec") or ""
            p["appearance_result"] = fields.get("appearance_result") or ""
            p["ph_label"] = fields.get("ph_label") or "PH VALUE"
            p["ph_spec"] = fields.get("ph_spec") or ""
            p["ph_result"] = fields.get("ph_result") or ""
            p["solid_label"] = fields.get("solid_label") or "SOLID CONTENT(%)"
            p["solid_spec"] = fields.get("solid_spec") or ""
            p["solid_result"] = fields.get("solid_result") or ""
            p["odour_label"] = fields.get("odour_label") or ""
            p["odour_spec"] = fields.get("odour_spec") or ""
            p["odour_result"] = fields.get("odour_result") or ""
            # 一票一 COA：PI 固定本票
            p["coa_pi_no"] = base_payload.get("pi_no") or p.get("coa_pi_no") or ""

            mapping = _build_mapping(p)
            _fill_workbook_on_sheet(ws, mapping)
