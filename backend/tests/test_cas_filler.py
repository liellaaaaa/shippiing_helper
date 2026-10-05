# -*- coding: utf-8 -*-
"""cas_filler 单元测试：合并预览阶段缺 CAS 自动补全"""
from app.core.cas_filler import fill_missing_cas


NAME_TO_CAS = {
    "水": "7732-18-5",
    "端环氧硅油": "9004-73-3",
    "聚二甲基硅氧烷（硅油）": "9016-00-6",
    "非离子乳化剂": "68439-50-9",
}


def test_fill_water_missing_cas():
    out, filled = fill_missing_cas("端环氧硅油 9004-73-3 90% + 水 10%", NAME_TO_CAS)
    assert out == "端环氧硅油 9004-73-3 90% + 水 7732-18-5 10%"
    assert filled == ["水"]


def test_keep_existing_cas_untouched():
    src = "聚二甲基硅氧烷（硅油）40%  9016-00-6，非离子乳化剂 8% 68439-50-9 ，水：7732-18-5 52%"
    out, filled = fill_missing_cas(src, NAME_TO_CAS)
    assert out == src
    assert filled == []


def test_keep_parenthesized_cas():
    src = "水（7732-18-5）10% + 端环氧硅油 9004-73-3 90%"
    out, filled = fill_missing_cas(src, NAME_TO_CAS)
    assert out == src
    assert filled == []


def test_unknown_component_left_as_is():
    out, filled = fill_missing_cas("未知成分 5% + 水 95%", NAME_TO_CAS)
    assert "未知成分 5%" in out
    assert "水 7732-18-5 95%" in out
    assert filled == ["水"]


def test_empty_text():
    assert fill_missing_cas("", NAME_TO_CAS) == ("", [])
    assert fill_missing_cas(None, NAME_TO_CAS) == ("", [])
