"""Tests for PI contract table parsing (parse_pi_contract_table)."""

import pytest

from app.core.order_parser import parse_pi_contract_table


# 企业微信在线表格复制格式：每行被拆成多物理行 ——
# 第1行 = 客户编码+PI号（2列），第2行起 = 业务员及后续列，成分列可能再拆多行
RAW_USER_DATA = (
    "WA495\tHT20260722RE\n"
    "\t卢泳因\t宏昊\t公路\t3000\t1.98\t5940\tK2-GB\t无色透明液体\t2942000000\t螯合分散剂\t三聚磷酸钠7758-29-4 40%\n"
    "葡萄糖酸钠527-07-1  10%\n"
    "水：7732-18-5 50%\t2026年7月30日\tTT 15\t\t\t\t\t\t\n"
    "WA495\tHT20260722RE\n"
    "\t卢泳因\t宏昊\t公路\t9000\t2.35\t21150\tF-128R\t黄色液体\t3403910000\t纺织柔软剂\t聚二甲基硅氧烷（硅油）40%  9016-00-6，非离子乳化剂 8% 68439-50-9 ，水：7732-18-5 52%\t\t\t\t\t\t\t\t\n"
    "WA495\tHT20260722RE\n"
    "\t卢泳因\t宏昊\t公路\t6000\t2.85\t17100\tF-182HQ\t黄色液体\t3403910000\t纺织柔软剂\t聚二甲基硅氧烷（硅油）45%  9016-00-6，非离子乳化剂 9% 68439-50-9 ，水：7732-18-5 46%\t\t\t\t\t\t\t\t\n"
    "WA495\tHT20260722RE\n"
    "\t卢泳因\t宏昊\t公路\t6000\t2.7\t16200\tA-77Y\t淡黄色粘稠液体\t3402420000\t匀染剂\t非离子表面活性剂68439-50-9  35%\n"
    "脂肪醇聚氧烷基醚68439-46-3  45%\n"
    "水：7732-18-5 20%"
)


def test_parse_pi_contract_table_multiline_row():
    """行首片段（客户编码+PI号）必须与续行合并解析，不能全部跳过"""
    orders, skipped, warning = parse_pi_contract_table(RAW_USER_DATA)
    assert len(orders) == 1, f"应解析出 1 个订单，实际 {len(orders)}，skipped={len(skipped)}"
    assert orders[0].order_no == "HT20260722RE"
    assert orders[0].customer_code == "WA495"
    codes = [item.internal_code for item in orders[0].items]
    assert codes == ["K2-GB", "F-128R", "F-182HQ", "A-77Y"]
    assert skipped == []


def test_parse_pi_contract_table_single_line_row():
    """单物理行格式（成分不含换行）仍应正常解析"""
    text = (
        "WA495\tHT20260722RE\t卢泳因\t宏昊\t公路\t9000\t2.35\t21150\t"
        "F-128R\t黄色液体\t3403910000\t纺织柔软剂\t"
        "聚二甲基硅氧烷（硅油）40%  9016-00-6，非离子乳化剂 8% 68439-50-9 ，水：7732-18-5 52%\t"
        "2026年7月30日\tTT 15"
    )
    orders, skipped, warning = parse_pi_contract_table(text)
    assert len(orders) == 1
    assert orders[0].items[0].internal_code == "F-128R"
    assert orders[0].items[0].quantity_kg == 9000
    assert orders[0].items[0].unit_price == 2.35
    assert orders[0].items[0].total_amount == 21150
    assert orders[0].items[0].hs_code == "3403910000"
    assert orders[0].items[0].customs_name == "纺织柔软剂"
    assert orders[0].pi_date == "2026年7月30日"
    assert orders[0].shipment_method == "公路"
    assert orders[0].shipment_title == "宏昊"
    assert orders[0].salesperson == "卢泳因"
