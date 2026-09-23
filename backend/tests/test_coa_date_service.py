from datetime import date

from app.services.coa_date_service import (
    parse_production_date_from_batch,
    compute_expiry_date,
)


def test_sa_batch_full():
    assert parse_production_date_from_batch("SA20260626017") == date(2026, 6, 26)


def test_sa_batch_other():
    assert parse_production_date_from_batch("SA20260713008") == date(2026, 7, 13)
    assert parse_production_date_from_batch("SA20260807038") == date(2026, 8, 7)


def test_sa_batch_date_only_no_seq():
    assert parse_production_date_from_batch("SA20260626") == date(2026, 6, 26)


def test_invalid_batch():
    assert parse_production_date_from_batch("") is None
    assert parse_production_date_from_batch(None) is None
    assert parse_production_date_from_batch("XX20260626017") is None
    assert parse_production_date_from_batch("SA20261332") is None


def test_expiry_plus_1y_minus_1d():
    assert compute_expiry_date(date(2026, 6, 26), "plus_1y_minus_1d") == date(2027, 6, 25)
    assert compute_expiry_date(date(2026, 7, 13), "plus_1y_minus_1d") == date(2027, 7, 12)


def test_expiry_plus_6m_minus_1d():
    assert compute_expiry_date(date(2026, 8, 7), "plus_6m_minus_1d") == date(2027, 2, 6)


def test_expiry_manual_or_unknown():
    assert compute_expiry_date(date(2026, 8, 7), "manual") is None
    assert compute_expiry_date(date(2026, 8, 7), "unknown_rule") is None
