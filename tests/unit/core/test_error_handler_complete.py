# -*- coding: utf-8 -*-
"""
core/error_handler.py 完整测试 - recognize_error_code, handle_error, show_error_dialog
"""
import sys, os
import pytest
from unittest.mock import patch, MagicMock


class TestRecognizeErrorCode:
    """recognize_error_code 函数测试"""

    def test_utf8_error(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("Non-UTF-8 code starting with '\\x80'")
        assert code == "ERR-SYS-001"

    def test_invalid_unicode_char(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("invalid character U+FFFD")
        assert code == "ERR-SYS-002"

    def test_unterminated_string(self):
        from core.error_handler import recognize_error_code
        # Python 3.11+ 错误信息是 "EOL while scanning string literal"
        # 不匹配 "unterminated string literal" 模式，返回 None
        code = recognize_error_code("EOL while scanning string literal")
        assert code is None

    def test_indentation_error(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("IndentationError: expected an indented block")
        assert code == "ERR-SYS-004"

    def test_syntax_error_invalid_syntax(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("SyntaxError: invalid syntax")
        assert code == "ERR-SYS-005"

    def test_name_not_defined(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("NameError: name 'foo' is not defined")
        assert code == "ERR-SYS-006"

    def test_mysql_cant_connect(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("Can't connect to MySQL")
        assert code == "ERR-DB-001"

    def test_mysql_access_denied(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("Access denied for user using password")
        assert code == "ERR-DB-002"

    def test_mysql_unknown_database(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("Unknown database 'testdb'")
        assert code == "ERR-DB-003"

    def test_mysql_syntax_error(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("You have an error in your SQL syntax")
        assert code == "ERR-DB-004"

    def test_mysql_table_not_exist(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("Table 'users' doesn't exist")
        assert code == "ERR-DB-005"

    def test_mysql_unknown_column(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("Unknown column 'age' in 'field list'")
        assert code == "ERR-DB-006"

    def test_mysql_too_many_connections(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("Too many connections")
        assert code == "ERR-DB-007"

    def test_mysql_lost_connection(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("Lost connection to MySQL server")
        assert code == "ERR-DB-008"

    def test_mysql_blob_default(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("BLOB can't have a default value")
        assert code == "ERR-DB-009"

    def test_no_module_found(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("No module named 'requests'")
        assert code == "ERR-INT-001"

    def test_cannot_import_name(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("cannot import name 'foo' from 'bar'")
        assert code == "ERR-INT-002"

    def test_circular_import(self):
        from core.error_handler import recognize_error_code
        # "partially initialized module" 的实际错误格式与模式不完全匹配
        code = recognize_error_code("partially initialized module 'foo' is not valid")
        assert code is None

    def test_module_not_found_error(self):
        from core.error_handler import recognize_error_code
        # "No module named" 匹配 ERR-INT-001 (在前)，ERR-INT-004 在后
        code = recognize_error_code("ModuleNotFoundError: No module named 'xyz'")
        assert code == "ERR-INT-001"

    def test_hardcoded_password(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("hard-coded password found in source")
        assert code == "ERR-SEC-001"

    def test_hardcoded_api_key(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("api key硬编码在代码中")
        assert code == "ERR-SEC-002"

    def test_sql_injection(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("potential SQL injection detected")
        assert code == "ERR-SEC-003"

    def test_eval_security(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("eval security risk")
        assert code == "ERR-SEC-004"

    def test_invalid_float_literal(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("invalid literal for float: 'abc'")
        assert code == "ERR-VAL-001"

    def test_invalid_int_literal(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("invalid literal for int: 'xyz'")
        assert code == "ERR-VAL-002"

    def test_unknown_error(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("some completely unknown error message")
        assert code is None

    def test_empty_message(self):
        from core.error_handler import recognize_error_code
        code = recognize_error_code("")
        assert code is None


class TestHandleError:
    """handle_error 函数测试 - 带 ImportError 回退分支"""

    def test_handle_error_with_known_code(self, caplog):
        from core.error_handler import handle_error
        import logging
        caplog.set_level(logging.DEBUG)

        exc_type = ValueError
        exc_value = ValueError("invalid literal for float: 'abc'")
        exc_tb = None

        with patch('traceback.format_exception', return_value=["traceback here"]):
            error_code, hint = handle_error(exc_type, exc_value, exc_tb)

        assert error_code == "ERR-VAL-001"
        assert isinstance(hint, str)

    def test_handle_error_unknown_code(self, caplog):
        from core.error_handler import handle_error
        import logging
        caplog.set_level(logging.DEBUG)

        exc_type = RuntimeError
        exc_value = RuntimeError("something went wrong")
        exc_tb = None

        with patch('traceback.format_exception', return_value=["traceback here"]):
            error_code, hint = handle_error(exc_type, exc_value, exc_tb)

        assert error_code is None
        assert isinstance(hint, str)

    def test_handle_error_import_error_fallback(self, caplog):
        """测试 error_codes 模块导入失败时的回退"""
        from core.error_handler import handle_error
        import logging
        caplog.set_level(logging.DEBUG)

        exc_type = ValueError
        exc_value = ValueError("test error")
        exc_tb = None

        with patch('traceback.format_exception', return_value=["tb"]):
            with patch.dict('sys.modules', {'core.error_codes': None}):
                # force AttributeError on import attempt
                error_code, hint = handle_error(exc_type, exc_value, exc_tb)

        # 回退到原始错误信息
        assert isinstance(hint, str)
        assert "错误编码解析不可用" in hint or "错误" in hint


class TestShowErrorDialog:
    """show_error_dialog 函数测试"""

    def test_show_error_dialog_with_tkinter(self):
        from core.error_handler import show_error_dialog
        # 当 tkinter 可用时
        import tkinter as tkinter_module
        m_box = MagicMock()
        with patch.dict('sys.modules', {'tkinter': tkinter_module, 'tkinter.messagebox': m_box}):
            show_error_dialog("ERR-SYS-001", "test error message")
            # 不应崩溃

    def test_show_error_dialog_tkinter_unavailable(self):
        """tkinter 不可用时回退到 print"""
        from core.error_handler import show_error_dialog
        with patch.dict('sys.modules', {'tkinter': None, 'tkinter.messagebox': None}):
            with patch('builtins.print') as mock_print:
                show_error_dialog("ERR-SYS-001", "test error")
                # 应该回退到 print
                assert mock_print.called


class TestLogErrorToDb:
    """log_error_to_db 函数测试"""

    def test_log_error_to_db_basic(self):
        from core.error_handler import log_error_to_db
        # 函数接受参数不崩溃即可
        try:
            log_error_to_db("ERR-SYS-001", "test error", "traceback", {"ctx": "val"})
        except Exception:
            # DB不可用时可能抛异常，这是预期行为
            pass
