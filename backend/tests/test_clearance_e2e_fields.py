"""对照 WA318 样例关键数字。"""
import io

import openpyxl

from app.schemas.ledger import LedgerItemSchema, LedgerRecordResponse
from app.services.clearance_doc_service import ClearanceDocService


def wa318_record() -> LedgerRecordResponse:
    return LedgerRecordResponse(
        id=1,
        order_no="HT260720SZ",
        customer_code="WA318",
        consignee_name="CHEMZONE CO., LTD.",
        consignee_address="26/1D TRAN QUY CAP ST., BINH LOI TRUNG WARD, HO CHI MINH CITY, VIETNAM",
        destination="HOCHIMINH(CAT LAI),VIETNAM",
        loading_port="NANSHA,CHINA",
        price_term="CIF  HOCHIMINH",
        payment_terms="100% TT AFTER SHIPMENT 30 DAYS",
        pi_date="2026-07-20",
        currency="USD",
        items=[
            LedgerItemSchema(
                internal_code="HT-016H",
                product_en="FIXING AGENT HT-016H",
                quantity_kg=4000.0,
                unit_price=2.6,
                total_amount=10400.0,
                hs_code="340241",
                packaging_name="125kg /drum",
                drum_count=32,
                pallet_count=8,
                net_weight_kg=4000.0,
                gross_weight_kg=4308.0,
                volume_cbm=7.92,
            )
        ],
        status="saved",
    )


def _text(content: bytes) -> str:
    return "\n".join(
        str(c.value)
        for ws in openpyxl.load_workbook(io.BytesIO(content)).worksheets
        for row in ws.iter_rows()
        for c in row
        if c.value is not None
    )


def test_wa318_ci_pl_alignment():
    svc = ClearanceDocService()
    ov = {
        "container_no": "WHLU5694625",
        "seal_no": "WHA4051188",
        "invoice_date": "2026-08-01",
        "show_bank_block": True,
    }
    ci, _, _ = svc.generate("ci", wa318_record(), "honghao", ov)
    pl, _, _ = svc.generate("pl", wa318_record(), "honghao", ov)
    ci_text = _text(ci)
    pl_text = _text(pl)
    for t in (ci_text, pl_text):
        assert "WHLU5694625" in t
    # V2 §8.1：CI 无毛重/体积；N.W./G.W./CBM 在 PL（G.W./7.920 另见 SI）
    assert "4308" in pl_text or "4308.0" in pl_text
    assert "7.92" in pl_text or "7.920" in pl_text
    assert "IN260720SZ" in ci_text
    assert "PL260720SZ" in pl_text
    assert "TOTAL 32 DRUMS PACKED ON 8 PALLETS ONLY." in ci_text
    assert "10400" in ci_text or "10400.0" in ci_text
