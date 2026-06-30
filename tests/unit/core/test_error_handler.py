# -*- coding: utf-8 -*-
"""冲刺30% - error_handler + logger 纯逻辑测试"""
import sys, os
import pytest
from unittest.mock import patch, MagicMock


class TestRecognizeErrorCode:
    def test_recognize_db_error(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("Can't connect to MySQL server") == "ERR-DB-001"

    def test_recognize_access_denied(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("Access denied for user: password yes") == "ERR-DB-002"

    def test_recognize_syntax_error(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("You have an error in your SQL syntax") == "ERR-DB-004"

    def test_recognize_module_not_found(self):
        from core.error_handler import recognize_error_code
        # "ModuleNotFoundError: No module named 'xxx'" has "No module named" which matches ERR-INT-001 first
        assert recognize_error_code("No module named 'xxx'") == "ERR-INT-001"

    def test_recognize_json_decode(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("JSONDecodeError: Expecting value") == "ERR-VAL-003"

    def test_recognize_connection_lost(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("Lost connection to MySQL during query") == "ERR-DB-008"

    def test_recognize_table_not_exist(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("Table 'orders' doesn't exist") == "ERR-DB-005"

    def test_recognize_unknown_column(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("Unknown column 'xyz' in 'field list'") == "ERR-DB-006"

    def test_recognize_float_error(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("invalid literal for float(): abc") == "ERR-VAL-001"

    def test_empty_returns_none(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("") is None
        assert recognize_error_code(None) is None

    def test_unrecognized_returns_none(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("some random unknown error message 123456") is None


class TestErrorContext:
    def test_context_manager_no_error(self):
        from core.error_handler import ErrorContext
        with ErrorContext("测试操作"):
            pass  # no exception
        assert True

    def test_context_manager_with_error_raises(self):
        from core.error_handler import ErrorContext
        with pytest.raises(ValueError):
            with ErrorContext("失败操作", raise_on_error=True):
                raise ValueError("test error")

    def test_context_manager_with_error_suppressed(self):
        from core.error_handler import ErrorContext
        with ErrorContext("可恢复操作", raise_on_error=False):
            raise ValueError("recoverable")


class TestSafeErrorHandle:
    def test_decorator_normal(self):
        from core.error_handler import safe_error_handle
        @safe_error_handle
        def ok_func():
            return 42
        assert ok_func() == 42

    def test_decorator_raises(self):
        from core.error_handler import safe_error_handle
        @safe_error_handle
        def bad_func():
            raise ValueError("expected")
        with pytest.raises(ValueError):
            bad_func()


class TestGetErrorLookupUrl:
    def test_lookup_url(self):
        from core.error_handler import get_error_lookup_url
        url = get_error_lookup_url("ERR-DB-001")
        assert "err-db-001" in url.lower()


class TestErrorPatterns:
    def test_sql_injection_pattern(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("possible SQL injection detected") == "ERR-SEC-003"

    def test_eval_risk(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("eval security risk found") == "ERR-SEC-004"
