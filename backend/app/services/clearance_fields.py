"""从台账记录 + overrides 组装清关四单填充字段。

TBD 约束（V2 §12）：
- TBD-2 COA PI No 默认留空，仅 overrides.coa_pi_no 写入
- TBD-1 pH 条件默认用报告/overrides，不写死 20%
"""
from datetime import date as _date
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.company_config import get_company_profile
from app.schemas.clearance import ClearanceOverrides
from app.schemas.ledger import LedgerRecordResponse
from app.services.coa_date_service import compute_expiry_date, parse_production_date_from_batch
from app.services.doc_no_service import to_invoice_no, to_packing_no


def _visible_items(record: LedgerRecordResponse) -> List:
    items = record.items or []
    return [
        it
        for it in items
        if not (
            getattr(it, "group_id", None) is not None
            and not getattr(it, "is_group_header", False)
        )
    ]


def _amount_words_usd(amount: float) -> str:
    """英文金额大写（美元）。样例风格：TOTAL USD TEN THOUSAND AND FOUR HUNDRED ONLY."""
    try:
        n = int(round(float(amount)))
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    ones = [
        "", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE",
        "TEN", "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN",
        "SEVENTEEN", "EIGHTEEN", "NINETEEN",
    ]
    tens = ["", "", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"]

    def under_1000(x: int) -> str:
        if x == 0:
            return ""
        if x < 20:
            return ones[x]
        if x < 100:
            t, o = divmod(x, 10)
            return tens[t] + (("-" + ones[o]) if o else "")
        h, r = divmod(x, 100)
        return ones[h] + " HUNDRED" + ((" AND " + under_1000(r)) if r else "")

    if n < 1000:
        words = under_1000(n)
    else:
        th, rest = divmod(n, 1000)
        words = under_1000(th) + " THOUSAND"
        if rest:
            words += " AND " + under_1000(rest)
    return f"TOTAL USD {words} ONLY."


def build_route(loading: str, dest: str, dest_style: str) -> Tuple[str, str]:
    """返回 (route 全串, route_to)。dest_style: port|country|custom。"""
    pol = (loading or "NANSHA, CHINA").strip()
    dest_raw = (dest or "").strip()
    if dest_style == "country":
        # 「城市, 国家」取国家段；单段且含国家名则原样
        if "," in dest_raw:
            to = dest_raw.split(",")[-1].strip()
        else:
            to = dest_raw
    else:  # port / custom 都先用港口原文；custom 由模板覆盖占位符
        to = dest_raw
    route = f"FROM {pol} TO {to}"
    return route, to


def build_totals_line(packages: Optional[int], pallets: Optional[int]) -> str:
    pk = int(packages or 0)
    pl = int(pallets or 0)
    if pk <= 0 and pl <= 0:
        return ""
    if pl <= 0:
        return f"TOTAL {pk} PACKAGES ONLY."
    return f"TOTAL {pk} DRUMS PACKED ON {pl} PALLETS ONLY."


def build_clearance_payload(
    record: LedgerRecordResponse,
    company_code: Optional[str] = None,
    overrides: Optional[Union[ClearanceOverrides, dict]] = None,
    dest_style: Optional[str] = None,
) -> Dict[str, Any]:
    if isinstance(overrides, dict):
        ov = ClearanceOverrides(**overrides)
    else:
        ov = overrides or ClearanceOverrides()

    company = get_company_profile(company_code)
    items = _visible_items(record)
    style = dest_style or ov.dest_style or "port"

    pi_no = record.order_no or ""
    # 台账可能 order_no 即 PI；名称与样例一致
    invoice_no = to_invoice_no(pi_no)
    packing_no = to_packing_no(pi_no)

    route, route_to = build_route(record.loading_port or "", record.destination or "", style)

    # 明细
    out_items: List[Dict[str, Any]] = []
    total_qty = 0.0
    total_amount = 0.0
    total_net = 0.0
    total_gross = 0.0
    total_cbm = 0.0
    total_drums = 0
    total_pallets = 0
    for i, it in enumerate(items, 1):
        qty = float(it.quantity_kg or it.net_weight_kg or 0)
        price = float(it.unit_price or 0)
        amount = float(it.total_amount or (qty * price))
        nw = float(it.net_weight_kg or qty or 0)
        gw = float(it.gross_weight_kg or nw or 0)
        cbm = float(it.volume_cbm or 0)
        drums = int(it.drum_count or 0)
        pallets = int(it.pallet_count or 0)
        total_qty += qty
        total_amount += amount
        total_net += nw
        total_gross += gw
        total_cbm += cbm
        total_drums += drums
        total_pallets += pallets
        desc = it.product_en or it.customs_name or it.product_cn or it.internal_code
        out_items.append(
            {
                "index": i,
                "desc": desc,
                "qty": qty,
                "price": price,
                "amount": amount,
                "hs_code": it.hs_code or "",
                "net_kg": nw,
                "gross_kg": gw,
                "cbm": cbm,
                "drums": drums,
                "pallets": pallets,
                "packaging": it.packaging_name or "",
                "packages_display": pallets if style == "port" else drums,  # 模板可再映射
            }
        )

    packages = ov.packages if ov.packages is not None else total_drums
    pallets = ov.pallets if ov.pallets is not None else total_pallets
    gross = ov.gross_kg if ov.gross_kg is not None else total_gross
    net = ov.net_kg if ov.net_kg is not None else total_net
    cbm = ov.measure_cbm if ov.measure_cbm is not None else total_cbm

    # COA 日期
    batch = ov.batch_no or ""
    prod_s = ov.prod_date or ""
    exp_s = ov.exp_date or ""
    if not prod_s and batch:
        pd = parse_production_date_from_batch(batch)
        prod_s = pd.isoformat() if pd else ""
    if not exp_s and prod_s and ov.expiry_rule:
        try:
            y, m, d = prod_s.split("-")
            ed = compute_expiry_date(_date(int(y), int(m), int(d)), ov.expiry_rule)
            exp_s = ed.isoformat() if ed else ""
        except ValueError:
            exp_s = ""

    show_bank = True if ov.show_bank_block is None else bool(ov.show_bank_block)
    bank = {
        "bank_line1": f"BENEFICIARY BANK : {company['bank_name_en']}" if show_bank and company.get("bank_name_en") else "",
        "bank_line2": f"BENEFICIARY BANK ADDRESS : {company['bank_address_en']}" if show_bank and company.get("bank_address_en") else "",
        "bank_line3": f"BENEFICIARY NAME : {company['name_en']}" if show_bank and company.get("name_en") else "",
        "bank_line4": f"BENEFICIARY COMPANY ADDRESS : {company['address_en']}" if show_bank and company.get("address_en") else "",
        "bank_line5": f"BENEFICIARY BANK A/C : {company['bank_account']}" if show_bank and company.get("bank_account") else "",
        "bank_line6": f"BENEFICIARY BANK SWIFT CODE : {company['bank_swift']}" if show_bank and company.get("bank_swift") else "",
    }

    tax_display = record.consignee_tel or ""  # 台账 tel 栏常放 TAX；组装为 TO 块

    return {
        "pi_no": pi_no,
        "invoice_no": invoice_no,
        "packing_no": packing_no,
        "invoice_date": ov.invoice_date or record.pi_date or "",
        "po_no": ov.po_no or "",
        "show_po": bool(ov.show_po) if ov.show_po is not None else bool(ov.po_no),
        "consignee_name": record.consignee_name or "",
        "consignee_addr": record.consignee_address or "",
        "consignee_tax": tax_display,
        "notify": record.consignee_name or "",
        "notify_addr": record.consignee_address or "",
        "price_term": record.price_term or "",
        "payment_terms": record.payment_terms or "",
        "currency": record.currency or "USD",
        "loading_port": record.loading_port or "NANSHA, CHINA",
        "discharge_port": (record.destination or "").strip(),
        "route": route,
        "route_to": route_to,
        "container_no": ov.container_no or "",
        "seal_no": ov.seal_no or "",
        "vessel": (ov.vessel or "") + ((" / " + ov.voyage) if ov.voyage else ""),
        "bl_no": ov.bl_no or "",
        "dest_agent_name": ov.dest_agent_name or "",
        "dest_agent_addr": ov.dest_agent_addr or "",
        "dest_agent_tax": ov.dest_agent_tax or "",
        "dest_agent_tel": ov.dest_agent_tel or "",
        "items": out_items,
        "total_qty": total_qty,
        "total_amount": total_amount,
        "amount_words": _amount_words_usd(total_amount),
        "net_kg": net,
        "gross_kg": gross,
        "volume_cbm": cbm,
        "packages": packages,
        "pallets": pallets,
        "totals_line": build_totals_line(packages, pallets),
        "hs_codes": " / ".join([it["hs_code"] for it in out_items if it["hs_code"]]),
        "product_name": out_items[0]["desc"] if out_items else "",
        "shipped_qty_text": f"{int(total_qty) if total_qty == int(total_qty) else total_qty}KG",
        "batch_no": batch,
        "prod_date": prod_s,
        "exp_date": exp_s,
        "coa_pi_no": ov.coa_pi_no or pi_no,  # 一票一 COA，固定本票 PI（录音确认）
        "ph_label": ov.ph_label or "",  # 默认取检测报告解析结果
        "solid_label": ov.solid_label or "SOLID CONTENT",
        "appearance_spec": ov.appearance_spec or "",
        "appearance_result": ov.appearance_result or "",
        "ph_spec": ov.ph_spec or "",
        "ph_result": ov.ph_result or "",
        "solid_spec": ov.solid_spec or "",
        "solid_result": ov.solid_result or "",
        "company_name_en": company["name_en"],
        "company_addr_en": company["address_en"],
        "company_tel_en": f"TEL: {company['phone_en']}     FAX: {company['fax_en']}",
        **bank,
    }
