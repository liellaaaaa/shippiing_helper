# backend/tests/test_booking_dedup.py
"""订舱单按产品中文名去重合并测试"""
import pytest


def dedup_names(customs_names: list[str]) -> list[str]:
    """模拟订舱单去重逻辑"""
    unique_names = list(dict.fromkeys(customs_names))
    return unique_names[:6]


def test_no_duplicates():
    """场景1：无同名产品"""
    customs_names = ["防染剂", "柔软剂", "分散剂"]
    expected = ["防染剂", "柔软剂", "分散剂"]
    assert dedup_names(customs_names) == expected


def test_all_duplicates():
    """场景2：全部同名"""
    customs_names = ["防染剂", "防染剂", "防染剂"]
    expected = ["防染剂"]
    assert dedup_names(customs_names) == expected


def test_partial_duplicates():
    """场景3：部分同名"""
    customs_names = ["防染剂", "防染剂", "柔软剂", "分散剂"]
    expected = ["防染剂", "柔软剂", "分散剂"]
    assert dedup_names(customs_names) == expected


def test_more_than_6_after_dedup():
    """场景4：超过6个去重后产品"""
    customs_names = ["A", "B", "C", "D", "E", "F", "G"]
    expected = ["A", "B", "C", "D", "E", "F"]  # 只取前6个
    assert dedup_names(customs_names) == expected


def test_empty_list():
    """场景5：空列表"""
    customs_names = []
    expected = []
    assert dedup_names(customs_names) == expected


def test_single_product():
    """场景6：单个产品"""
    customs_names = ["防染剂"]
    expected = ["防染剂"]
    assert dedup_names(customs_names) == expected


def test_preserve_order():
    """场景7：保持原始顺序"""
    customs_names = ["柔软剂", "防染剂", "柔软剂", "分散剂", "防染剂"]
    expected = ["柔软剂", "防染剂", "分散剂"]
    assert dedup_names(customs_names) == expected
