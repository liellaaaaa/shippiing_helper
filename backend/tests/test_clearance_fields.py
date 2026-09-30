from app.schemas.ledger import LedgerItemSchema, LedgerRecordResponse
from app.services.clearance_fields import _amount_words_usd, build_clearance_payload


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
    assert p["totals_line"] == "TOTAL: 32 DRUMS PACKED ON 8 PALLETS"
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


def test_amount_words_basic():
    assert _amount_words_usd(1) == "TOTAL USD ONE ONLY."
    assert _amount_words_usd(7000) == "TOTAL USD SEVEN THOUSAND ONLY."
    assert _amount_words_usd(10400) == "TOTAL USD TEN THOUSAND AND FOUR HUNDRED ONLY."


def test_amount_words_million_scale_no_index_error():
    # S4: n>=2,000,000 曾触发 ones[h] 越界；1,234,567 曾错写成 TWELVE HUNDRED…
    assert _amount_words_usd(1234567) == (
        "TOTAL USD ONE MILLION TWO HUNDRED AND THIRTY-FOUR THOUSAND"
        " AND FIVE HUNDRED AND SIXTY-SEVEN ONLY."
    )
    assert _amount_words_usd(2000000) == "TOTAL USD TWO MILLION ONLY."
    assert _amount_words_usd(12345678) == (
        "TOTAL USD TWELVE MILLION THREE HUNDRED AND FORTY-FIVE THOUSAND"
        " AND SIX HUNDRED AND SEVENTY-EIGHT ONLY."
    )
    # 不得抛异常
    for v in (1, 1234567, 2000000, 12345678, 1_000_000_000):
        _amount_words_usd(v)


def test_amount_words_keeps_cents():
    assert _amount_words_usd(1.25) == "TOTAL USD ONE AND TWENTY-FIVE CENTS ONLY."
    assert _amount_words_usd(1234.56) == (
        "TOTAL USD ONE THOUSAND AND TWO HUNDRED AND THIRTY-FOUR"
        " AND FIFTY-SIX CENTS ONLY."
    )
    assert _amount_words_usd(0.5) == "TOTAL USD FIFTY CENTS ONLY."
    # 无小数时不追加 CENTS
    assert "CENTS" not in _amount_words_usd(2000000)


def test_amount_words_invalid_input():
    assert _amount_words_usd(0) == ""
    assert _amount_words_usd(-1) == ""
    assert _amount_words_usd(None) == ""
    assert _amount_words_usd("abc") == ""
