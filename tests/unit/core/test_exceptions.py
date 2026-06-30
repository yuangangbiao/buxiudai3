# -*- coding: utf-8 -*-
"""core/exceptions.py 依赖注入 - 安全执行函数测试"""
import pytest
from unittest.mock import MagicMock


# ============================================================
# BusinessException
# ============================================================
class TestBusinessException:
    def test_basic(self):
        from core.exceptions import BusinessException
        e = BusinessException("E001", "订单创建失败")
        assert e.code == "E001"
        assert e.message == "订单创建失败"
        assert e.details == {}

    def test_with_details(self):
        from core.exceptions import BusinessException
        e = BusinessException("E001", "错误", {"field": "name"})
        assert e.details == {"field": "name"}

    def test_str_with_details(self):
        from core.exceptions import BusinessException
        e = BusinessException("E001", "错误", {"field": "name"})
        assert "[E001] 错误" in str(e)
        assert "field" in str(e)

    def test_str_without_details(self):
        from core.exceptions import BusinessException
        e = BusinessException("E001", "错误")
        assert str(e) == "[E001] 错误"

    def test_to_dict(self):
        from core.exceptions import BusinessException
        e = BusinessException("E001", "错误", {"a": 1})
        d = e.to_dict()
        assert d["code"] == "E001"
        assert d["message"] == "错误"
        assert d["details"] == {"a": 1}


# ============================================================
# ValidationException
# ============================================================
class TestValidationException:
    def test_basic(self):
        from core.exceptions import ValidationException
        e = ValidationException("名称不能为空")
        assert e.code == "VALIDATION_ERROR"
        assert e.field is None

    def test_with_field(self):
        from core.exceptions import ValidationException
        e = ValidationException("不能为空", field="order_no")
        assert e.field == "order_no"
        assert "order_no" in str(e)

    def test_with_details(self):
        from core.exceptions import ValidationException
        e = ValidationException("超长", field="name", details={"max": 50})
        assert e.details == {"max": 50}


# ============================================================
# NotFoundException
# ============================================================
class TestNotFoundException:
    def test_basic(self):
        from core.exceptions import NotFoundException
        e = NotFoundException("订单", "ORD-001")
        assert e.code == "NOT_FOUND"
        assert e.resource == "订单"
        assert e.identifier == "ORD-001"
        assert "不存在" in str(e)


# ============================================================
# DuplicateException
# ============================================================
class TestDuplicateException:
    def test_basic(self):
        from core.exceptions import DuplicateException
        e = DuplicateException("订单号", "ORD-001")
        assert e.code == "DUPLICATE"
        assert e.resource == "订单号"
        assert "已存在" in str(e)


# ============================================================
# PermissionException
# ============================================================
class TestPermissionException:
    def test_default(self):
        from core.exceptions import PermissionException
        e = PermissionException()
        assert e.code == "PERMISSION_DENIED"
        assert e.message == "权限不足"

    def test_custom_message(self):
        from core.exceptions import PermissionException
        e = PermissionException("无权删除")
        assert e.message == "无权删除"


# ============================================================
# StateException
# ============================================================
class TestStateException:
    def test_basic(self):
        from core.exceptions import StateException
        e = StateException("状态不允许")
        assert e.code == "STATE_ERROR"
        assert e.current_state is None
        assert e.target_state is None

    def test_with_states(self):
        from core.exceptions import StateException
        e = StateException("不可转换", current_state="pending", target_state="shipped")
        assert e.current_state == "pending"
        assert e.target_state == "shipped"


# ============================================================
# DatabaseException
# ============================================================
class TestDatabaseException:
    def test_basic(self):
        from core.exceptions import DatabaseException
        e = DatabaseException("连接超时")
        assert e.code == "DATABASE_ERROR"
        assert e.sql is None

    def test_with_sql(self):
        from core.exceptions import DatabaseException
        e = DatabaseException("查询失败", sql="SELECT * FROM orders")
        assert e.sql == "SELECT * FROM orders"


# ============================================================
# ConfigException
# ============================================================
class TestConfigException:
    def test_basic(self):
        from core.exceptions import ConfigException
        e = ConfigException("配置缺失")
        assert e.code == "CONFIG_ERROR"
        assert e.config_key is None

    def test_with_key(self):
        from core.exceptions import ConfigException
        e = ConfigException("缺失", config_key="MYSQL_HOST")
        assert e.config_key == "MYSQL_HOST"


# ============================================================
# safe_cursor_execute
# ============================================================
class TestSafeCursorExecute:
    def test_success(self):
        from core.exceptions import safe_cursor_execute
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.execute.return_value = 3
        mock_conn.cursor.return_value = mock_cursor

        r = safe_cursor_execute(mock_conn, "DELETE FROM t WHERE id=%s", (1,))
        assert r == 3
        mock_conn.commit.assert_called_once()

    def test_error_rollback(self):
        from core.exceptions import safe_cursor_execute
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = RuntimeError("db error")
        mock_conn.cursor.return_value = mock_cursor

        r = safe_cursor_execute(mock_conn, "BAD SQL")
        assert r == 0  # default_return
        mock_conn.rollback.assert_called_once()


# ============================================================
# safe_cursor_insert
# ============================================================
class TestSafeCursorInsert:
    def test_success(self):
        from core.exceptions import safe_cursor_insert
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.lastrowid = 42
        mock_conn.cursor.return_value = mock_cursor

        r = safe_cursor_insert(mock_conn, "INSERT INTO t VALUES (%s)", ("val",))
        assert r == 42
        mock_conn.commit.assert_called_once()

    def test_error_returns_none(self):
        from core.exceptions import safe_cursor_insert
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = RuntimeError("db down")
        mock_conn.cursor.return_value = mock_cursor

        r = safe_cursor_insert(mock_conn, "INSERT ...")
        assert r is None
        mock_conn.rollback.assert_called_once()


# ============================================================
# handle_exceptions decorator
# ============================================================
class TestHandleExceptions:
    def test_normal_flow(self):
        from core.exceptions import handle_exceptions
        @handle_exceptions
        def f(x):
            return x * 2
        assert f(5) == 10

    def test_business_exception_passthrough(self):
        from core.exceptions import handle_exceptions, BusinessException
        @handle_exceptions
        def f():
            raise BusinessException("E001", "业务错误")
        with pytest.raises(BusinessException) as exc:
            f()
        assert exc.value.code == "E001"

    def test_general_exception_wraps(self):
        from core.exceptions import handle_exceptions, DatabaseException
        @handle_exceptions
        def f():
            raise ValueError("something wrong")
        with pytest.raises(DatabaseException) as exc:
            f()
        assert exc.value.code == "DATABASE_ERROR"


# ============================================================
# validation_required decorator
# ============================================================
class TestValidationRequired:
    def test_all_fields_present(self):
        from core.exceptions import validation_required
        @validation_required("name", "qty")
        def f(data=None):
            return "ok"
        assert f(data={"name": "test", "qty": 10}) == "ok"

    def test_missing_field_raises(self):
        from core.exceptions import validation_required, ValidationException
        @validation_required("name", "qty")
        def f(data=None):
            return "ok"
        with pytest.raises(ValidationException) as exc:
            f(data={"name": "test"})
        assert "缺少必填字段" in exc.value.message
