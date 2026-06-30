# -*- coding: utf-8 -*-
"""测试 models/database/utils_db.py"""
import pytest
from unittest.mock import patch, MagicMock
from models.database.utils_db import _validate_sql_identifier, _safe_table_name


class TestValidateSqlIdentifier:
    """测试 _validate_sql_identifier()"""

    def test_empty_string(self):
        assert _validate_sql_identifier("") is False

    def test_none(self):
        assert _validate_sql_identifier(None) is False

    def test_valid_identifier(self):
        assert _validate_sql_identifier("orders") is True
        assert _validate_sql_identifier("_valid_123") is True
        assert _validate_sql_identifier("TBL_2024") is True
        assert _validate_sql_identifier("a") is True

    def test_invalid_identifier(self):
        assert _validate_sql_identifier("123abc") is False
        assert _validate_sql_identifier("table name") is False
        assert _validate_sql_identifier("drop;") is False
        assert _validate_sql_identifier("") is False
        assert _validate_sql_identifier("中文字段") is False
        assert _validate_sql_identifier("a-b") is False


class TestSafeTableName:
    """测试 _safe_table_name()"""

    def test_valid_table(self):
        assert _safe_table_name("orders") == "orders"
        assert _safe_table_name("status_change_logs") == "status_change_logs"

    def test_invalid_table(self):
        with pytest.raises(ValueError, match="无效的表名"):
            _safe_table_name("")
        with pytest.raises(ValueError, match="无效的表名"):
            _safe_table_name("123abc")
        with pytest.raises(ValueError, match="无效的表名"):
            _safe_table_name("drop table")


class TestGenerateOrderNo:
    """测试 generate_order_no()"""

    def test_generates_order_no_with_new_row(self):
        """正常 case：orders 表已有记录，取 cnt+1"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"cnt": 5}

        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            result = _run_generate_order_no()

        assert result.startswith("ORD-")
        mock_cursor.execute.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_generates_order_no_no_row(self):
        """orders 表无记录时 seq=1"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            result = _run_generate_order_no()

        assert result.startswith("ORD-")
        assert result.endswith("-0001")
        mock_conn.close.assert_called_once()


class TestGenerateShipmentNo:
    """测试 generate_shipment_no()"""

    def test_generates_shipment_no(self):
        """正常 case"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"cnt": 3}

        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            result = _run_generate_shipment_no()

        assert result.startswith("SH-")
        assert result.endswith("-0004")
        mock_cursor.execute.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_generates_shipment_no_no_row(self):
        """无记录时 seq=1"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            result = _run_generate_shipment_no()

        assert result.startswith("SH-")
        assert result.endswith("-0001")
        mock_conn.close.assert_called_once()


class TestLogStatusChange:
    """测试 log_status_change()"""

    def test_logs_status_change(self):
        """正常记录状态变更"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            from models.database.utils_db import log_status_change
            log_status_change("orders", 42, "pending", "approved", "张三")

        mock_cursor.execute.assert_called_once()
        args, _ = mock_cursor.execute.call_args
        assert "INSERT INTO status_change_logs" in args[0]
        assert args[1][0] == "orders"
        assert args[1][1] == 42
        assert args[1][2] == "pending"
        assert args[1][3] == "approved"
        assert args[1][4] == "张三"
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_logs_status_change_default_operator(self):
        """operator 不传时默认 'system'"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            from models.database.utils_db import log_status_change
            log_status_change("orders", 1, "a", "b")

        args, _ = mock_cursor.execute.call_args
        assert args[1][4] == "system"

    def test_logs_exception_suppressed(self):
        """数据库异常时被 except 捕获，不抛给调用方"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB error")

        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            from models.database.utils_db import log_status_change
            # 不应抛出异常
            log_status_change("orders", 1, "old", "new")

        mock_conn.close.assert_called_once()

    def test_logs_exception_none_values(self):
        """old_status/new_status 为 None 时转为空字符串"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            from models.database.utils_db import log_status_change
            log_status_change("orders", 1, None, None, "admin")

        args, _ = mock_cursor.execute.call_args
        assert args[1][2] == ""
        assert args[1][3] == ""
        mock_conn.close.assert_called_once()


# 提取公共辅助函数
from datetime import datetime


def _run_generate_order_no():
    """调用 generate_order_no 并返回结果"""
    from models.database.utils_db import generate_order_no
    return generate_order_no()


def _run_generate_shipment_no():
    """调用 generate_shipment_no 并返回结果"""
    from models.database.utils_db import generate_shipment_no
    return generate_shipment_no()
