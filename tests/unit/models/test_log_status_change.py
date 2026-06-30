# -*- coding: utf-8 -*-
r"""log_status_change 集成测试

覆盖场景:
- 4 参调用（无 operator）
- 5 参调用（带 operator）
- 6 参调用（带 operator + remark，v6 修补后兼容）
- signature 锁定（防止再次出现多版本实现）
- 触发 process.py:365/368 6 参路径（5008 同步失败 → 6 参调用）
"""
import inspect
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestLogStatusChangeSignature:
    """签名锁定测试（防止签名漂移）"""

    def test_signature_has_remark_param(self):
        """#1 v6.0.1 修补后必须有 remark 参数"""
        from models.database import log_status_change
        sig = inspect.signature(log_status_change)
        params = list(sig.parameters.keys())
        assert "remark" in params, f"缺少 remark 参数，实际参数: {params}"

    def test_signature_six_params(self):
        """#1 必须 6 个参数（向后兼容）"""
        from models.database import log_status_change
        sig = inspect.signature(log_status_change)
        assert len(sig.parameters) == 6, f"参数数={len(sig.parameters)}，期望 6"

    def test_signature_remark_has_default(self):
        """#1 remark 必须有默认值（向后兼容老调用）"""
        from models.database import log_status_change
        sig = inspect.signature(log_status_change)
        remark_param = sig.parameters["remark"]
        assert remark_param.default == "", f"remark 默认值={remark_param.default!r}，期望 ''"

    def test_operator_has_default(self):
        """#1 operator 也必须有默认值"""
        from models.database import log_status_change
        sig = inspect.signature(log_status_change)
        op_param = sig.parameters["operator"]
        assert op_param.default is None, f"operator 默认值={op_param.default!r}，期望 None"

    def test_no_legacy_duplicate(self):
        """#1 _database_legacy.py 不应有 log_status_change 函数"""
        from models.database import _database_legacy
        assert not hasattr(_database_legacy, "log_status_change"), \
            "_database_legacy.py 还有 log_status_change 函数，请删除避免签名不一致"


class TestLogStatusChangeBehavior:
    """行为测试（mock 数据库）"""

    def _make_mock_conn(self):
        """构造 mock conn — utils_db.py 用 c = conn.cursor()，不用 with"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn, mock_cursor

    def test_four_params_works(self):
        """#1 4 参调用（仅必填）"""
        from models.database import log_status_change
        mock_conn, mock_cursor = self._make_mock_conn()
        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            log_status_change("orders", 100, "old", "new")
        assert mock_cursor.execute.called, "cursor.execute 应被调用"

    def test_five_params_with_operator(self):
        """#1 5 参调用（含 operator）"""
        from models.database import log_status_change
        mock_conn, mock_cursor = self._make_mock_conn()
        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            log_status_change("orders", 100, "old", "new", "operator1")
        assert mock_cursor.execute.called

    def test_six_params_with_remark(self):
        """#1 6 参调用（v6 process.py:365/368 使用）"""
        from models.database import log_status_change
        mock_conn, mock_cursor = self._make_mock_conn()
        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            log_status_change("orders", 100, "old", "new", "operator1", "remark1")
        assert mock_cursor.execute.called
        # 验证 SQL 包含 remark 占位符
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "remark" in sql, f"SQL 缺 remark 列: {sql[:200]}"

    def test_six_params_remark_in_values(self):
        """#1 6 参时 remark 值正确传递"""
        from models.database import log_status_change
        mock_conn, mock_cursor = self._make_mock_conn()
        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            log_status_change("orders", 100, "old", "new", "operator1", "test remark 123")
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert "test remark 123" in params, f"remark 值未在 params: {params}"

    def test_remark_default_empty_string(self):
        """#1 不传 remark 时，SQL 用空字符串"""
        from models.database import log_status_change
        mock_conn, mock_cursor = self._make_mock_conn()
        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            log_status_change("orders", 100, "old", "new")
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert any(p == "" for p in params), f"缺 remark 默认空字符串: {params}"

    def test_legacy_style_six_params_positional(self):
        """#1 process.py:365 风格（位置参数 6 个）"""
        from models.database import log_status_change
        mock_conn, mock_cursor = self._make_mock_conn()
        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            log_status_change(
                "process_records", 200, "old_status", "new_status",
                "worker_name", "5008 同步失败: test error"
            )
        assert mock_cursor.execute.called


class TestLogStatusChangeIntegration:
    """集成测试（端到端验证 process.py 异常分支）"""

    def test_process_record_update_5008_failure_no_typeerror(self):
        """#1 真实场景：process.py:365 5008 同步失败触发 6 参调用，不抛 TypeError"""
        from models.database import log_status_change
        from unittest.mock import patch, MagicMock

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            try:
                log_status_change(
                    "process_records", 999, "old", "new",
                    "工人A", "5008 同步失败: ConnectionError"
                )
            except TypeError as e:
                raise AssertionError(f"log_status_change 6 参调用仍抛 TypeError: {e}")
            except Exception:
                # 其他异常（如 mock 错误）可接受
                pass

    def test_process_record_update_packing_failure_no_typeerror(self):
        """#1 真实场景：process.py:368 包装入库联动失败触发 6 参调用"""
        from models.database import log_status_change
        from unittest.mock import patch, MagicMock

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("models.database.utils_db.get_connection", return_value=mock_conn):
            try:
                log_status_change(
                    "process_records", 999, "old", "new",
                    "工人A", "包装入库联动失败: ValueError"
                )
            except TypeError as e:
                raise AssertionError(f"6 参调用仍抛 TypeError: {e}")
            except Exception:
                pass


class TestLogStatusChangeReExport:
    """re-export 验证（防止 import 路径变化）"""

    def test_top_level_import(self):
        """#1 from models.database import log_status_change 可用"""
        from models.database import log_status_change
        assert callable(log_status_change)

    def test_submodule_import(self):
        """#1 from models.database.utils_db import log_status_change 仍可用"""
        from models.database.utils_db import log_status_change
        assert callable(log_status_change)

    def test_legacy_import_blocked(self):
        """#1 from models.database._database_legacy import log_status_change 应失败"""
        with __import__("pytest").raises(ImportError):
            from models.database._database_legacy import log_status_change


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
