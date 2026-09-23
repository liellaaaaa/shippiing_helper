import pytest

from app.schemas.ledger import LedgerItemSchema, LedgerRecordResponse
from app.services.clearance_doc_service import _build_mapping
from app.services.clearance_fields import build_clearance_payload


def _item(
    code: str,
    desc: str,
    qty: float,
    price: float,
    amount: float,
    hs: str,
    net: float,
    gross: float,
    cbm: float,
    drums: int,
    pallets: int,
) -> LedgerItemSchema:
    return LedgerItemSchema(
        internal_code=code,
        product_en=desc,
        quantity_kg=qty,
        unit_price=price,
        total_amount=amount,
        hs_code=hs,
        drum_count=drums,
        pallet_count=pallets,
        net_weight_kg=net,
        gross_weight_kg=gross,
        volume_cbm=cbm,
    )


def make_single_record() -> LedgerRecordResponse:
    return LedgerRecordResponse(
        id=1,
        order_no="HT260720SZ",
        customer_code="WA318",
        consignee_name="CHEMZONE CO., LTD.",
        consignee_address="26/1D TRAN QUY CAP ST., HO CHI MINH CITY, VIETNAM",
        consignee_tel="TAX CODE: 0316699088",
        destination="HOCHIMINH(CAT LAI), VIETNAM",
        loading_port="NANSHA, CHINA",
        price_term="CIF HOCHIMINH",
        payment_terms="100% TT AFTER SHIPMENT 30 DAYS",
        pi_date="2026-07-20",
        currency="USD",
        items=[
            _item("FIX-HT016H", "FIXING AGENT HT-016H", 4000.0, 2.6, 10400.0, "340241", 4000.0, 4308.0, 7.92, 32, 8)
        ],
        status="saved",
    )


def make_three_item_record() -> LedgerRecordResponse:
    return LedgerRecordResponse(
        id=2,
        order_no="HT260801SZ",
        customer_code="WA318",
        consignee_name="CHEMZONE CO., LTD.",
        consignee_address="26/1D TRAN QUY CAP ST., HO CHI MINH CITY, VIETNAM",
        consignee_tel="TAX CODE: 0316699088",
        destination="HOCHIMINH(CAT LAI), VIETNAM",
        loading_port="NANSHA, CHINA",
        price_term="CIF HOCHIMINH",
        payment_terms="100% TT AFTER SHIPMENT 30 DAYS",
        pi_date="2026-08-01",
        currency="USD",
        items=[
            _item("A-001", "PRODUCT ALPHA", 1000.0, 1.5, 1500.0, "340241", 1000.0, 1080.0, 1.8, 8, 2),
            _item("B-002", "PRODUCT BETA", 2000.0, 2.0, 4000.0, "380894", 2000.0, 2160.0, 3.6, 16, 4),
            _item("C-003", "PRODUCT GAMMA", 500.0, 3.0, 1500.0, "290545", 500.0, 540.0, 0.9, 4, 1),
        ],
        status="saved",
    )


def test_three_item_mapping_has_indexed_keys():
    p = build_clearance_payload(record=make_three_item_record(), company_code="honghao", overrides={})
    m = _build_mapping(p)

    assert m["ITEM_COUNT"] == "3"
    for i, (desc, qty, price, amount, hs) in enumerate(
        [
            ("PRODUCT ALPHA", 1000.0, 1.5, 1500.0, "340241"),
            ("PRODUCT BETA", 2000.0, 2.0, 4000.0, "380894"),
            ("PRODUCT GAMMA", 500.0, 3.0, 1500.0, "290545"),
        ],
        start=1,
    ):
        assert m[f"ITEM_NO_{i}"] == str(i)
        assert m[f"ITEM_DESC_{i}"] == desc
        assert float(m[f"ITEM_QTY_{i}"]) == qty
        assert float(m[f"ITEM_PRICE_{i}"]) == price
        assert float(m[f"ITEM_AMOUNT_{i}"]) == amount
        assert m[f"ITEM_HS_{i}"] == hs

    # PL extras
    assert m["ITEM_PACKAGES_1"] == "2"
    assert m["ITEM_PACKAGES_2"] == "4"
    assert m["ITEM_PACKAGES_3"] == "1"
    assert float(m["ITEM_CBM_1"]) == 1.8
    assert float(m["ITEM_NET_2"]) == 2000.0
    assert float(m["ITEM_GROSS_3"]) == 540.0

    # legacy aliases point at item 1
    assert m["ITEM_DESC"] == m["ITEM_DESC_1"]
    assert m["ITEM_QTY"] == m["ITEM_QTY_1"]
    assert m["ITEM_PRICE"] == m["ITEM_PRICE_1"]
    assert m["ITEM_AMOUNT"] == m["ITEM_AMOUNT_1"]

    # no item 4 keys
    assert "ITEM_DESC_4" not in m
    assert "ITEM_NO_4" not in m


def test_single_item_still_fills_legacy_aliases():
    p = build_clearance_payload(record=make_single_record(), company_code="honghao", overrides={})
    m = _build_mapping(p)

    assert m["ITEM_COUNT"] == "1"
    assert m["ITEM_DESC"] == "FIXING AGENT HT-016H"
    assert m["ITEM_QTY"] == "4000.0"
    assert m["ITEM_PRICE"] == "2.6"
    assert m["ITEM_AMOUNT"] == "10400.0"
    assert m["ITEM_NO_1"] == "1"
    assert m["ITEM_DESC_1"] == "FIXING AGENT HT-016H"
    assert m["ITEM_HS_1"] == "340241"
    assert m["HS_CODES"] == "340241"


def test_totals_sum_all_three_items():
    p = build_clearance_payload(record=make_three_item_record(), company_code="honghao", overrides={})
    assert p["total_qty"] == 3500.0
    assert p["total_amount"] == 7000.0
    assert p["net_kg"] == 3500.0
    assert p["gross_kg"] == 3780.0
    assert p["volume_cbm"] == pytest.approx(6.3)
    assert p["packages"] == 28
    assert p["pallets"] == 7
    assert p["totals_line"] == "TOTAL 28 DRUMS PACKED ON 7 PALLETS ONLY."
    assert p["amount_words"] == "TOTAL USD SEVEN THOUSAND ONLY."
