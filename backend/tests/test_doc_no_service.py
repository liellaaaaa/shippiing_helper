from app.services.doc_no_service import to_invoice_no, to_packing_no


def test_ht_prefix_to_in():
    assert to_invoice_no("HT260720SZ") == "IN260720SZ"


def test_hh_prefix_to_in():
    assert to_invoice_no("HH12345") == "IN12345"


def test_mh_prefix_keeps_region():
    assert to_invoice_no("MHBD260304") == "INBD260304"


def test_in_idempotent():
    assert to_invoice_no("IN260720SZ") == "IN260720SZ"


def test_no_prefix_from_first_digit():
    assert to_invoice_no("XX260304E01") == "IN260304E01"


def test_empty():
    assert to_invoice_no("") == ""
    assert to_invoice_no(None) == ""


def test_packing_no_ht():
    assert to_packing_no("HT260720SZ") == "PL260720SZ"


def test_packing_no_idempotent():
    assert to_packing_no("PL260720SZ") == "PL260720SZ"


def test_packing_no_mh():
    assert to_packing_no("MHBD260304") == "PLBD260304"
