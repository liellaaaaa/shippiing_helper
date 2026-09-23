from app.schemas.ledger import LedgerItemSchema, LedgerRecordResponse
from app.services.clearance_fields import build_clearance_payload


def make_record() -> LedgerRecordResponse:
    return LedgerRecordResponse(
        id=1,
        order_no="HT260720SZ",
        customer_code="WA318",
        sales_person="lw",
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
            LedgerItemSchema(
                internal_code="FIX-HT016H",
                product_en="FIXING AGENT HT-016H",
                product_cn="固色剂",
                quantity_kg=4000.0,
                unit_price=2.6,
                total_amount=10400.0,
                hs_code="340241",
                packaging_name="125kg/drum",
                drum_count=32,
                pallet_count=8,
                net_weight_kg=4000.0,
                gross_weight_kg=4308.0,
                volume_cbm=7.92,
            )
        ],
        status="saved",
    )


def test_basic_numbers():
    p = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={
            "container_no": "WHLU5694625",
            "seal_no": "WHA4051188",
            "invoice_date": "2026-08-01",
        },
    )
    assert p["pi_no"] == "HT260720SZ"
    assert p["invoice_no"] == "IN260720SZ"
    assert p["packing_no"] == "PL260720SZ"
    assert p["container_no"] == "WHLU5694625"
    assert p["totals_line"] == "TOTAL 32 DRUMS PACKED ON 8 PALLETS ONLY."
    assert p["items"][0]["desc"] == "FIXING AGENT HT-016H"
    assert p["items"][0]["amount"] == 10400.0


def test_route_dest_style_country():
    p = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={},
        dest_style="country",
    )
    # VIETNAM 已是国家；country 风格仍输出 ROUTE TO 含国家
    assert "NANSHA" in p["route"]
    assert "VIETNAM" in p["route_to"]


def test_overrides_measure_win():
    p = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={"gross_kg": 4400.0, "measure_cbm": 8.0, "pallets": 8, "packages": 32},
    )
    assert p["gross_kg"] == 4400.0
    assert p["volume_cbm"] == 8.0


def test_coa_dates_from_batch_and_rule():
    p = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={
            "batch_no": "SA20260626017",
            "expiry_rule": "plus_1y_minus_1d",
        },
    )
    assert p["prod_date"] == "2026-06-26"
    assert p["exp_date"] == "2027-06-25"


def test_coa_pi_no_defaults_to_shipment_pi():
    """一票一 COA：默认填本票 PI（录音确认，不再是 TBD）。"""
    p = build_clearance_payload(record=make_record(), company_code="honghao", overrides={})
    assert p["coa_pi_no"] == "HT260720SZ"
    p2 = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={"coa_pi_no": "HT260616SZ"},
    )
    assert p2["coa_pi_no"] == "HT260616SZ"


def test_bank_block_flag():
    p = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={"show_bank_block": True},
    )
    assert p["bank_line1"].startswith("BENEFICIARY BANK")
    p_off = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={"show_bank_block": False},
    )
    assert p_off["bank_line1"] == ""
