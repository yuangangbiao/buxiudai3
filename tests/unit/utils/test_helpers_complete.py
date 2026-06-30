# -*- coding: utf-8 -*-
"""
utils/helpers.py 测试 - 覆盖缺口: L70 (format_amount)
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch


class TestHelpersFormatAmount:
    """format_amount 函数测试 - 覆盖L70"""

    def test_format_amount_none(self):
        from utils.helpers import format_amount
        assert format_amount(None) == "0.00"

    def test_format_amount_zero(self):
        from utils.helpers import format_amount
        assert format_amount(0) == "0.00"

    def test_format_amount_integer(self):
        from utils.helpers import format_amount
        assert format_amount(100) == "100.00"

    def test_format_amount_float(self):
        from utils.helpers import format_amount
        assert format_amount(123.456) == "123.46"

    def test_format_amount_string(self):
        from utils.helpers import format_amount
        assert format_amount("999") == "999.00"


class TestHelpersGetUrgencyColor:
    """get_urgency_color 函数测试"""

    @patch('utils.helpers.date')
    def test_overdue(self, mock_date):
        mock_date.today.return_value = date(2026, 5, 29)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        from utils.helpers import get_urgency_color
        # 5月27日已过期2天
        result = get_urgency_color("2026-05-27")
        assert result == "#F44336"

    @patch('utils.helpers.date')
    def test_urgent_3_days(self, mock_date):
        mock_date.today.return_value = date(2026, 5, 29)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        from utils.helpers import get_urgency_color
        # 6月1日还有3天
        result = get_urgency_color("2026-06-01")
        assert result == "#FF5722"

    @patch('utils.helpers.date')
    def test_approaching_7_days(self, mock_date):
        mock_date.today.return_value = date(2026, 5, 29)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        from utils.helpers import get_urgency_color
        # 6月4日还有6天
        result = get_urgency_color("2026-06-04")
        assert result == "#FF9800"

    @patch('utils.helpers.date')
    def test_sufficient_time(self, mock_date):
        mock_date.today.return_value = date(2026, 5, 29)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        from utils.helpers import get_urgency_color
        # 6月20日还有22天
        result = get_urgency_color("2026-06-20")
        assert result == "#4CAF50"

    def test_empty_date(self):
        from utils.helpers import get_urgency_color
        # 空日期默认绿色
        assert get_urgency_color("") == "#4CAF50"

    def test_invalid_date(self):
        from utils.helpers import get_urgency_color
        assert get_urgency_color("invalid") == "#4CAF50"


class TestHelpersDaysUntil:
    """days_until 函数测试"""

    @patch('utils.helpers.date')
    def test_future_date(self, mock_date):
        mock_date.today.return_value = date(2026, 5, 29)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        from utils.helpers import days_until
        assert days_until("2026-06-05") == 7

    @patch('utils.helpers.date')
    def test_past_date(self, mock_date):
        mock_date.today.return_value = date(2026, 5, 29)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        from utils.helpers import days_until
        assert days_until("2026-05-20") == -9

    @patch('utils.helpers.date')
    def test_today(self, mock_date):
        mock_date.today.return_value = date(2026, 5, 29)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        from utils.helpers import days_until
        assert days_until("2026-05-29") == 0

    def test_empty_string(self):
        from utils.helpers import days_until
        assert days_until("") == 999


class TestHelpersValidateDate:
    """validate_date 函数测试"""

    def test_valid_yyyy_mm_dd(self):
        from utils.helpers import validate_date
        ok, val, err = validate_date("2026-05-29")
        assert ok is True
        assert val == "2026-05-29"

    def test_valid_yyyy_slash(self):
        from utils.helpers import validate_date
        ok, val, err = validate_date("2026/05/29")
        assert ok is True
        assert val == "2026-05-29"

    def test_valid_yyyy_dot(self):
        from utils.helpers import validate_date
        ok, val, err = validate_date("2026.05.29")
        assert ok is True
        assert val == "2026-05-29"

    def test_invalid_format(self):
        from utils.helpers import validate_date
        ok, val, err = validate_date("29-05-2026")
        assert ok is False
        assert "YYYY-MM-DD" in err

    def test_empty_not_allowed(self):
        from utils.helpers import validate_date
        ok, val, err = validate_date("", allow_empty=False)
        assert ok is False
        assert "不能为空" in err

    def test_empty_allowed(self):
        from utils.helpers import validate_date
        ok, val, err = validate_date("", allow_empty=True)
        assert ok is True


class TestHelpersFormatDate:
    """format_date 函数测试"""

    def test_valid_date(self):
        from utils.helpers import format_date
        assert format_date("2026-05-29") == "2026-05-29"

    def test_empty_returns_default(self):
        from utils.helpers import format_date
        assert format_date("", default="N/A") == "N/A"

    def test_invalid_date(self):
        from utils.helpers import format_date
        # 无效日期原样返回
        assert format_date("invalid") == "invalid"
