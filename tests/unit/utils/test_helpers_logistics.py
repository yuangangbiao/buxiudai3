# -*- coding: utf-8 -*-
"""helpers.py + logistics_companies.py 纯逻辑测试"""
import pytest
import os
import tempfile
from unittest.mock import patch
from datetime import date


# ============================================================
# helpers.py
# ============================================================
class TestValidateNumber:
    def test_valid_int(self):
        from utils.helpers import validate_number
        ok, val, msg = validate_number("42")
        assert ok is True
        assert val == 42.0

    def test_valid_float(self):
        from utils.helpers import validate_number
        ok, val, _ = validate_number("3.14")
        assert ok is True
        assert val == 3.14

    def test_empty_allowed(self):
        from utils.helpers import validate_number
        ok, val, _ = validate_number("")
        assert ok is True
        assert val is None

    def test_empty_not_allowed(self):
        from utils.helpers import validate_number
        ok, val, msg = validate_number("", allow_empty=False)
        assert ok is False
        assert "不能为空" in msg

    def test_below_min(self):
        from utils.helpers import validate_number
        ok, _, msg = validate_number("3", min_val=5)
        assert ok is False
        assert "不能小于" in msg

    def test_above_max(self):
        from utils.helpers import validate_number
        ok, _, msg = validate_number("200", max_val=100)
        assert ok is False
        assert "不能大于" in msg

    def test_invalid_string(self):
        from utils.helpers import validate_number
        ok, _, msg = validate_number("abc")
        assert ok is False
        assert "有效数字" in msg


class TestValidateDate:
    def test_iso_date(self):
        from utils.helpers import validate_date
        ok, val, _ = validate_date("2025-12-31")
        assert ok is True
        assert val == "2025-12-31"

    def test_slash_date(self):
        from utils.helpers import validate_date
        ok, val, _ = validate_date("2025/06/15")
        assert ok is True
        assert val == "2025-06-15"

    def test_dot_date(self):
        from utils.helpers import validate_date
        ok, val, _ = validate_date("2025.01.01")
        assert ok is True
        assert val == "2025-01-01"

    def test_empty_allowed(self):
        from utils.helpers import validate_date
        ok, val, _ = validate_date("")
        assert ok is True

    def test_empty_not_allowed(self):
        from utils.helpers import validate_date
        ok, _, msg = validate_date("", allow_empty=False)
        assert ok is False

    def test_invalid(self):
        from utils.helpers import validate_date
        ok, _, msg = validate_date("not-a-date")
        assert ok is False
        assert "YYYY-MM-DD" in msg


class TestFormatDate:
    def test_valid_date(self):
        from utils.helpers import format_date
        assert format_date("2025-06-01") == "2025-06-01"

    def test_empty(self):
        from utils.helpers import format_date
        assert format_date("") == ""

    def test_with_default(self):
        from utils.helpers import format_date
        assert format_date("", default="N/A") == "N/A"


class TestDaysUntil:
    def test_future_date(self):
        from utils.helpers import days_until
        d = days_until("2099-12-31")
        assert d > 0

    def test_past_date(self):
        from utils.helpers import days_until
        d = days_until("2020-01-01")
        assert d < 0

    def test_empty(self):
        from utils.helpers import days_until
        assert days_until("") == 999

    def test_invalid(self):
        from utils.helpers import days_until
        assert days_until("bad") == 999


class TestUrgencyColor:
    def test_overdue_red(self):
        from utils.helpers import get_urgency_color
        assert get_urgency_color("2020-01-01") == "#F44336"

    def test_future_green(self):
        from utils.helpers import get_urgency_color
        assert get_urgency_color("2099-12-31") == "#4CAF50"


class TestFormatAmount:
    def test_normal(self):
        from utils.helpers import format_amount
        assert "1,234.56" in format_amount(1234.56)

    def test_none(self):
        from utils.helpers import format_amount
        assert format_amount(None) == "0.00"


class TestFormatSpec:
    def test_full_spec(self):
        from utils.helpers import format_spec
        order = {"width": 100, "length": 50, "wire_diameter": 2.5, "mesh_size": 12}
        spec = format_spec(order)
        assert "宽100mm" in spec
        assert "长50m" in spec
        assert "丝径2.5mm" in spec
        assert "节距12mm" in spec

    def test_extra_params_fallback(self):
        from utils.helpers import format_spec
        order = {"extra_params": {"总宽": 200, "网带段数": 80}}
        spec = format_spec(order)
        assert "宽200mm" in spec
        assert "长80m" in spec

    def test_empty(self):
        from utils.helpers import format_spec
        assert format_spec({}) == "规格待填"


class TestTruncateText:
    def test_short(self):
        from utils.helpers import truncate_text
        assert truncate_text("hello") == "hello"

    def test_long(self):
        from utils.helpers import truncate_text
        t = truncate_text("a" * 50, max_len=10)
        assert len(t) == 10

    def test_empty(self):
        from utils.helpers import truncate_text
        assert truncate_text("") == ""


# ============================================================
# logistics_companies.py
# ============================================================
class TestLogistics:
    def test_default_list(self):
        from utils.logistics_companies import DEFAULT_LOGISTICS
        assert len(DEFAULT_LOGISTICS) >= 10
        assert "顺丰速运" in DEFAULT_LOGISTICS

    def test_get_all_includes_defaults(self):
        from utils.logistics_companies import get_all_companies
        companies = get_all_companies()
        assert "顺丰速运" in companies
        assert "德邦物流" in companies

    def test_add_invalid_empty(self):
        from utils.logistics_companies import add_company
        ok, msg = add_company("")
        assert ok is False
        assert "不能为空" in msg

    def test_add_duplicate(self):
        from utils.logistics_companies import add_company
        ok, msg = add_company("顺丰速运")
        assert ok is False
        assert "已存在" in msg

    def test_remove_default_not_allowed(self):
        from utils.logistics_companies import remove_company
        ok, msg = remove_company("顺丰速运")
        assert ok is False
        assert "不可删除" in msg

    def test_remove_nonexistent(self):
        from utils.logistics_companies import remove_company
        ok, msg = remove_company("不存在的公司abc123")
        assert ok is False
        assert "不存在" in msg

    def test_get_custom(self):
        from utils.logistics_companies import get_custom_companies
        custom = get_custom_companies()
        assert isinstance(custom, list)
