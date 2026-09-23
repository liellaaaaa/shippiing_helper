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


def _build_si_desc_block(
    items: List[Dict[str, Any]],
    total_qty: float,
    packages: Optional[int],
    pallets: Optional[int],
) -> str:
    """补料货描块：单品「品名+NET WEIGHT+H.S.CODE+TOTAL」；多品「序号.品名 / HS / QTY」。

    对齐船务部补料成品（WA254 单品块、BLUETEC 多品编号列表）。
    """
    if not items:
        return ""
    if len(items) == 1:
        it = items[0]
        nw = it.get("net_kg") or it.get("qty") or 0
        qty_txt = f"{int(nw) if float(nw) == int(float(nw)) else nw}"
        hs = it.get("hs_code") or ""
        totals = build_totals_line(packages, pallets)
        parts = [it.get("desc") or "", f"NET WEIGHT:{qty_txt}KGS"]
        if hs:
            parts.append(f"H.S.CODE:{hs}")
        if totals:
            parts.append(totals)
        return "\n".join(parts)
    lines: List[str] = []
    for i, it in enumerate(items, 1):
        q = it.get("qty") or 0
        q_txt = f"{int(q) if float(q) == int(float(q)) else q}"
        lines.append(f"{i}.{it.get('desc') or ''}")
        if it.get("hs_code"):
            lines.append(f"H.S. Code : {it['hs_code']}")
        lines.append(f"QTY:{q_txt}KGS")
    totals = build_totals_line(packages, pallets)
    if totals:
        lines.append(totals)
    return "\n".join(lines)


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
    package_unit = (ov.package_unit or "pallets").strip().lower()
    if package_unit not in ("pallets", "drums"):
        package_unit = "pallets"

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
        # 缺单价/金额时留空，不打 0.0（船务反馈：LEVELLING AGENT 第三行 0.0 混乱）
        price_raw = it.unit_price
        price: Optional[float] = float(price_raw) if price_raw is not None else None
        amount_raw = it.total_amount
        if amount_raw is not None:
            amount: Optional[float] = float(amount_raw)
        elif price is not None:
            amount = qty * price
        else:
            amount = None
        nw = float(it.net_weight_kg or qty or 0)
        gw = float(it.gross_weight_kg or nw or 0)
        cbm = float(it.volume_cbm or 0)
        drums = int(it.drum_count or 0)
        pallets = int(it.pallet_count or 0)
        total_qty += qty
        if amount is not None:
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
                "internal_code": it.internal_code or "",
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
                # 无包装数据留空，不打 0
                "packages_display": (pallets if package_unit == "pallets" else drums) or "",
            }
        )

    # 同名产品（如两条 LEVELLING AGENT）用内部编号区分，避免发票看起来像重复行
    seen_desc: dict[str, int] = {}
    for it in out_items:
        seen_desc[it["desc"]] = seen_desc.get(it["desc"], 0) + 1
    for it in out_items:
        if seen_desc.get(it["desc"], 0) > 1 and it["internal_code"]:
            if it["internal_code"] not in it["desc"]:
                it["desc"] = f"{it['desc']} {it['internal_code']}"

    packages = ov.packages if ov.packages is not None else total_drums
    pallets = ov.pallets if ov.pallets is not None else total_pallets
    packages_display = pallets if package_unit == "pallets" else packages
    gross = ov.gross_kg if ov.gross_kg is not None else round(total_gross, 3)
    net = ov.net_kg if ov.net_kg is not None else round(total_net, 3)
    cbm = ov.measure_cbm if ov.measure_cbm is not None else round(total_cbm, 3)
    total_qty = round(total_qty, 3)
    total_amount = round(total_amount, 2)

    # 装箱号区间：单排 1-N；多排按件数累计 1-84 / 85-109（对齐 PL HT260721A01）
    pk_display = int(packages_display or 0)
    if len(out_items) <= 1:
        packing_range = f"1-{pk_display}" if pk_display > 1 else ("1" if pk_display == 1 else "")
    else:
        start = 1
        for i, it in enumerate(out_items, 1):
            n = int(it.get("packages_display") or 0)
            if n <= 0:
                it["packing_range"] = str(i)
                continue
            end = start + n - 1
            it["packing_range"] = f"{start}-{end}" if end > start else str(start)
            start = end + 1
        packing_range = ""

    # 无包装数据时留空，不打 0（截图里 PACKING QTY=0 / CBM=0.000 显得混乱）
    if not packages_display:
        packages_display_out: Any = ""
    else:
        packages_display_out = packages_display
    volume_out: Any = "" if not cbm else round(cbm, 3)
    packages_out: Any = "" if not packages else packages

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
        "packages": packages_out,
        "pallets": pallets,
        "package_unit": package_unit,
        "packages_display": packages_display_out,
        "volume_cbm": volume_out,
        "totals_line": build_totals_line(packages, pallets),
        "hs_codes": " / ".join([it["hs_code"] for it in out_items if it["hs_code"]]),
        "product_name": out_items[0]["desc"] if out_items else "",
        "shipped_qty_text": f"{int(total_qty) if total_qty == int(total_qty) else total_qty}KG",
        "si_desc_block": _build_si_desc_block(out_items, total_qty, packages, pallets),
        "marks": getattr(ov, "marks", None) or "N/M",
        "remark": getattr(ov, "remark", None) or "",
        "package_unit_label": "PALLET(S)" if package_unit == "pallets" else "DRUMS",
        "final_dest": (record.destination or "").strip(),
        "container_qty": getattr(ov, "container_qty", None) or "",
        "packing_range": packing_range,
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
