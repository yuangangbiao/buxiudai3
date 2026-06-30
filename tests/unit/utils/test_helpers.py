# -*- coding: utf-8 -*-
r"""utils/helpers.py 的集成测试。

真源码行为(已读 d:\yuan\不锈钢网带跟单3.0\utils\helpers.py 验证):
- validate_number(value, allow_empty=True, min_val=None, max_val=None) 返 (is_valid, num, error_msg)
- validate_date(value, allow_empty=True) 返 (is_valid, "YYYY-MM-DD", "") 支持 YYYY-MM-DD/YYYY/MM/DD/YYYY.MM.DD
- format_date(date_str, default="") 格式化
- days_until(date_str) 返 999 如果空/无效,否则 (date - today).days
- get_urgency_color(date_str) 返 hex:#F44336 / #FF5722 / #FF9800 / #4CAF50
- format_amount(amount) 返 "1,234.56"
- format_spec(order) 返 "宽...mm | 长...m | 丝径...mm | 节距...mm"
- truncate_text(text, max_len=20) 截断过长文本

按 F16 §1:不 mock 业务路径,真函数验证。
"""
from datetime import date, timedelta

import pytest

from utils.helpers import (
    validate_number, validate_date, format_date,
    days_until, get_urgency_color,
    format_amount, format_spec, truncate_text,
)


def test_validate_number_empty_allowed():
    r"""validate_number 空值 + allow_empty=True 返 (True, None, "")。"""
    assert validate_number("") == (True, None, "")
    assert validate_number(None) == (True, None, "")


def test_validate_number_empty_not_allowed():
    r"""validate_number 空值 + allow_empty=False 返 (False, None, "此字段不能为空")。"""
    assert validate_number("", allow_empty=False) == (False, None, "此字段不能为空")


def test_validate_number_valid_value():
    r"""validate_number 有效数字返 (True, num, "")。"""
    assert validate_number("123.45") == (True, 123.45, "")


def test_validate_number_below_min():
    r"""validate_number < min_val 返 (False, None, "值不能小于 X")。"""
    assert validate_number("5", min_val=10) == (False, None, "值不能小于 10")


def test_validate_number_above_max():
    r"""validate_number > max_val 返 (False, None, "值不能大于 X")。"""
    assert validate_number("101", max_val=100) == (False, None, "值不能大于 100")


def test_validate_number_non_numeric():
    r"""validate_number 非数字返 (False, None, "请输入有效数字")。"""
    assert validate_number("abc") == (False, None, "请输入有效数字")


def test_validate_date_empty_allowed():
    r"""validate_date 空值 + allow_empty=True 返 (True, "", "")。"""
    assert validate_date("") == (True, "", "")


def test_validate_date_empty_not_allowed():
    r"""validate_date 空值 + allow_empty=False 返 (False, "", "日期不能为空")。"""
    assert validate_date("", allow_empty=False) == (False, "", "日期不能为空")


def test_validate_date_dash_format():
    r"""validate_date 'YYYY-MM-DD' 格式 返 (True, normalized, "")。"""
    assert validate_date("2026-06-12") == (True, "2026-06-12", "")


def test_validate_date_slash_format():
    r"""validate_date 'YYYY/MM/DD' 格式 规范化到 'YYYY-MM-DD'。"""
    assert validate_date("2026/06/12") == (True, "2026-06-12", "")


def test_validate_date_dot_format():
    r"""validate_date 'YYYY.MM.DD' 格式 规范化到 'YYYY-MM-DD'。"""
    assert validate_date("2026.06.12") == (True, "2026-06-12", "")


def test_validate_date_invalid_format():
    r"""validate_date 无效格式 返 (False, "", "日期格式应为 YYYY-MM-DD")。"""
    assert validate_date("20260612") == (False, "", "日期格式应为 YYYY-MM-DD")


def test_format_date_returns_default_for_empty():
    r"""format_date 空字符串返 default(源码第 45 行 if not date_str)。"""
    assert format_date("") == ""
    assert format_date("", default="fallback") == "fallback"


def test_format_date_invalid_returns_input_as_is():
    r"""format_date 无效日期原样返(源码第 50 行 except Exception: return date_str)。
    注意:不返 default,只返 date_str。
    """
    assert format_date("not_a_date") == "not_a_date"
    assert format_date("not_a_date", default="fallback") == "not_a_date"


def test_format_date_normalizes_valid():
    r"""format_date 有效日期返 YYYY-MM-DD 格式。"""
    assert format_date("2026-06-12T10:00:00") == "2026-06-12"


def test_days_until_returns_999_for_empty():
    r"""days_until 空字符串返 999(源码第 56 行)。"""
    assert days_until("") == 999


def test_days_until_returns_999_for_invalid():
    r"""days_until 无效日期返 999。"""
    assert days_until("not_a_date") == 999


def test_days_until_today_is_zero():
    r"""days_until 今天日期返 0。"""
    today_str = date.today().strftime("%Y-%m-%d")
    assert days_until(today_str) == 0


def test_days_until_future_positive():
    r"""days_until 未来日期返正数。"""
    future = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    assert days_until(future) == 10


def test_days_until_past_negative():
    r"""days_until 过去日期返负数。"""
    past = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
    assert days_until(past) == -5


def test_get_urgency_color_overdue_red():
    r"""get_urgency_color 过期日期 (<0) 返红色 #F44336。"""
    past = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert get_urgency_color(past) == "#F44336"


def test_get_urgency_color_urgent_dark_orange():
    r"""get_urgency_color 紧急(<=3) 返深橙 #FF5722。"""
    assert get_urgency_color(date.today().strftime("%Y-%m-%d")) == "#FF5722"
    future3 = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")
    assert get_urgency_color(future3) == "#FF5722"


def test_get_urgency_color_near_orange():
    r"""get_urgency_color 临近(<=7) 返橙色 #FF9800。"""
    future5 = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
    assert get_urgency_color(future5) == "#FF9800"


def test_get_urgency_color_sufficient_green():
    r"""get_urgency_color 充裕(>7) 返绿色 #4CAF50。"""
    future30 = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    assert get_urgency_color(future30) == "#4CAF50"


def test_format_amount_none_returns_zero():
    r"""format_amount None 返 "0.00"。"""
    assert format_amount(None) == "0.00"


def test_format_amount_thousands_separator():
    r"""format_amount 大数字带千分位。"""
    assert format_amount(1234567.89) == "1,234,567.89"


def test_format_amount_small_value():
    r"""format_amount 小数 保留 2 位。"""
    assert format_amount(99.5) == "99.50"


def test_format_spec_empty_returns_default():
    r"""format_spec 全空字段返 '规格待填'(源码第 99 行)。"""
    assert format_spec({}) == "规格待填"


def test_format_spec_english_fields():
    r"""format_spec width/length/wire_diameter/mesh_size 英文字段。"""
    order = {
        "width": 1000, "length": 50,
        "wire_diameter": 1.5, "mesh_size": 5,
    }
    assert format_spec(order) == "宽1000mm | 长50m | 丝径1.5mm | 节距5mm"


def test_format_spec_chinese_fields_via_extra_params():
    r"""format_spec 总宽/网带段数/钢丝直径/网带节距 中文字段(extra_params 内)。"""
    order = {
        "extra_params": {
            "总宽": 1000, "网带段数": 50,
            "钢丝直径": 1.5, "网带节距": 5,
        }
    }
    assert format_spec(order) == "宽1000mm | 长50m | 丝径1.5mm | 节距5mm"


def test_format_spec_partial_fields():
    r"""format_spec 部分字段时只显示有值的部分(其他跳过)。"""
    order = {"width": 800, "mesh_size": 5}
    assert format_spec(order) == "宽800mm | 节距5mm"


def test_truncate_text_short_passthrough():
    r"""truncate_text 短文本原样返。"""
    assert truncate_text("hello", max_len=20) == "hello"


def test_truncate_text_exact_length():
    r"""truncate_text 等于 max_len 原样返(源码第 106 行 <= max_len)。"""
    assert truncate_text("12345", max_len=5) == "12345"


def test_truncate_text_long_truncated():
    r"""truncate_text 超长文本截断 + 加省略号。"""
    assert truncate_text("abcdefghij", max_len=5) == "abcd…"


def test_truncate_text_empty():
    r"""truncate_text 空字符串返 ""。"""
    assert truncate_text("") == ""
    assert truncate_text(None) == ""
