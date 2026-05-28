"""Tests for order_parser.py."""

import pytest
from app.core.order_parser import (
    normalize_column_name,
    parse_pasted_data,
)


def test_parse_single_order_single_item():
    text = """订单号\t客户编号\t内部编号\t产品中文名\t规格kg\t订单量kg\t单价/kg
HT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂\t25\t2400\t29.5"""
    orders, skipped, warning = parse_pasted_data(text)
    assert len(orders) == 1
    assert orders[0].order_no == "HT260304E01"
    assert len(orders[0].items) == 1
    assert orders[0].items[0].internal_code == "SILI-001"


def test_parse_single_order_multiple_items():
    text = """订单号\t客户编号\t内部编号\t产品中文名\t规格kg\t订单量kg
HT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂A\t25\t2400
HT260304E01\tTOA-DOVECHEM\tSILI-002\t有机硅柔软剂B\t50\t1600"""
    orders, skipped, warning = parse_pasted_data(text)
    assert len(orders) == 1
    assert len(orders[0].items) == 2


def test_parse_batch_dedup():
    text = """订单号\t客户编号\t内部编号\t产品中文名\t订单量kg
HT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂\t1000
HT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂\t2000"""
    orders, skipped, warning = parse_pasted_data(text)
    assert warning is not None
    assert len(orders[0].items) == 1
    assert orders[0].items[0].quantity_kg == 2000  # later entry overwrites earlier


def test_parse_missing_internal_code_skipped():
    text = """订单号\t客户编号\t内部编号\t产品中文名
HT260304E01\tTOA-DOVECHEM\tSILI-001\t有机硅柔软剂
HT260304E01\tTOA-DOVECHEM\t\t改性硅油"""
    orders, skipped, warning = parse_pasted_data(text)
    assert len(skipped) == 1


def test_normalize_column_name():
    assert normalize_column_name("订单号") == "order_no"
    assert normalize_column_name("Order No") == "order_no"
    assert normalize_column_name("H.S.Code") == "hs_code"