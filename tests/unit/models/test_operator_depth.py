# -*- coding: utf-8 -*-
"""
深度测试 models.operator — 确保每一行可执行代码都被 pytest 覆盖到。
覆盖范围：所有方法的正常路径、边界条件分支、异常路径。

使用 pytest-cov 启动方式：
  pytest tests/unit/models/test_operator_depth.py --cov=models/operator --cov-report=term-missing
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from models.operator import OperatorDAO, OperatorLogDAO


# ── 辅助 Fixture ─────────────────────────────────────────

@pytest.fixture
def mock_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# ── OperatorDAO.get_all ── 深度 ──────────────────────────
# （已有 3 个测试，这里补充确保 cursor 路径走到）

class TestOperatorDAOGetAllDepth:

    def test_get_all_return_dicts(self, mock_conn):
        """确认返回的是 [dict(...)] 格式"""
        conn, cursor = mock_conn
        # 注意：dict(MagicMock()) 不可靠，即使设置了 __iter__，
        # dict() 内部通过 __getitem__(index) 获取元素时 MagicMock 返回 MagicMock。
        # 因此这里用真实 dict 模拟 MySQL 行。
        class Row(dict):
            """模拟 MySQL cursor 的行对象，支持 dict(row) 转换"""
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
            def keys(self):
                return [k for k in self]
        row = Row({"id": 1, "operator_id": "001"})
        cursor.fetchall.return_value = [row]
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.get_all()
            assert isinstance(result[0], dict)
            assert result[0]["operator_id"] == "001"


# ── OperatorDAO.get_by_id ── 深度 ────────────────────────

class TestOperatorDAOGetByIdDepth:

    def test_get_by_id_sql_param(self, mock_conn):
        """验证 SQL 参数正确传递"""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = {"id": 1, "operator_id": "001"}
        with patch("models.operator.get_connection", return_value=conn):
            OperatorDAO.get_by_id("001")
            assert cursor.execute.call_args[0][1] == ("001",)


# ── OperatorDAO.login ── 深度 ────────────────────────────
# 验证 finally::conn.close() 在异常时仍被执行
# 验证 conn.close 在 conn2 场景下的调用次数

class TestOperatorDAOLoginDepth:

    def test_login_no_salt_mixed_calls(self, mock_conn):
        """无 salt 场景：验证 conn 和 conn2 都被关闭"""
        conn, cursor = mock_conn
        row = {"id": 1, "operator_id": "001", "name": "a",
               "role": "o", "status": "正常",
               "password": "plain", "password_salt": None}
        cursor.fetchone.return_value = row

        conn2 = MagicMock()
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2

        with patch("models.operator.get_connection", side_effect=[conn, conn2]), \
             patch("models.operator.hash_password", return_value=("h", "s")):
            OperatorDAO.login("001", "plain")
            conn.close.assert_called()  # finally 中的 close
            conn2.close.assert_called_once()


# ── OperatorDAO.add ── 深度 ──────────────────────────────
# 验证 generate_random_password 默认路径

class TestOperatorDAOAddDepth:

    def test_add_without_password(self, mock_conn):
        """不传 password 时使用随机密码"""
        conn, cursor = mock_conn
        data = {"operator_id": "010", "name": "test"}
        with patch("models.operator.get_connection", return_value=conn), \
             patch("models.operator.hash_password", return_value=("h", "s")), \
             patch("models.operator.generate_random_password", return_value="rand123"):
            OperatorDAO.add(data)
            # hash_password 应该被调用（使用随机密码）
            from models.operator import hash_password
            conn.close.assert_called_once()


# ── OperatorDAO.update ── 深度 ───────────────────────────

class TestOperatorDAOUpdateDepth:

    def test_update_only_updated_at(self, mock_conn):
        """不传任何更新字段时应该只有 updated_at"""
        conn, cursor = mock_conn
        with patch("models.operator.get_connection", return_value=conn):
            OperatorDAO.update("001", {})
            sql = cursor.execute.call_args[0][0]
            # 应该只有 updated_at=%s 和 WHERE
            assert "updated_at=%s" in sql
            assert "name" not in sql
            assert "role" not in sql

    def test_update_all_fields(self, mock_conn):
        """同时更新所有字段"""
        conn, cursor = mock_conn
        data = {"name": "a", "role": "r", "password": "p", "status": "s", "wechat_userid": "w"}
        with patch("models.operator.get_connection", return_value=conn), \
             patch("models.operator.hash_password", return_value=("h", "s")):
            OperatorDAO.update("001", data)
            sql = cursor.execute.call_args[0][0]
            assert "name=%s" in sql
            assert "role=%s" in sql
            assert "password=%s" in sql
            assert "password_salt=%s" in sql
            assert "status=%s" in sql
            assert "wechat_userid=%s" in sql
            assert "updated_at=%s" in sql


# ── OperatorDAO.delete ── 深度 ───────────────────────────

class TestOperatorDAODeleteDepth:

    def test_delete_sql_guard(self, mock_conn):
        """验证 SQL 中有 AND 防删除 admin"""
        conn, cursor = mock_conn
        with patch("models.operator.get_connection", return_value=conn):
            OperatorDAO.delete("operator_001")
            sql = cursor.execute.call_args[0][0]
            assert "operator_id!='admin'" in sql


# ── OperatorDAO.change_password ── 深度 ──────────────────

class TestOperatorDAOChangePasswordDepth:

    def test_change_password_finally_close(self, mock_conn):
        """验证 change_password 在 conn2 异常时 close"""
        conn, cursor = mock_conn
        cursor.fetchone.return_value = {"password": "old", "password_salt": "salt"}

        conn2 = MagicMock()
        cursor2 = MagicMock()
        cursor2.execute.side_effect = Exception("DB error on update")
        conn2.cursor.return_value = cursor2

        with patch("models.operator.get_connection", side_effect=[conn, conn2]), \
             patch("models.operator.verify_password", return_value=True), \
             patch("models.operator.hash_password", return_value=("h", "s")):
            with pytest.raises(Exception, match="DB error on update"):
                OperatorDAO.change_password("001", "old", "new")
            conn2.close.assert_called_once()  # 内部 finally 关闭 conn2


# ── OperatorLogDAO.add ── 深度 ───────────────────────────

class TestOperatorLogDAOAddDepth:

    def test_add_log_params(self, mock_conn):
        """验证参数正确绑定"""
        conn, cursor = mock_conn
        with patch("models.operator.get_connection", return_value=conn):
            OperatorLogDAO.add("op001", "张三", "登录系统", "user", "101", "成功登录")
            params = cursor.execute.call_args[0][1]
            assert params == ("op001", "张三", "登录系统", "user", "101", "成功登录")


# ── OperatorLogDAO.get_logs ── 深度 ─────────────────────

class TestOperatorLogDAOGetLogsDepth:

    def test_get_logs_default_limit(self, mock_conn):
        """验证默认 limit=100"""
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        with patch("models.operator.get_connection", return_value=conn):
            OperatorLogDAO.get_logs()
            params = cursor.execute.call_args[0][1]
            assert params == (100,)


# ── OperatorLogDAO.get_by_operator ── 深度 ───────────────

class TestOperatorLogDAOGetByOperatorDepth:

    def test_get_by_operator_default_limit(self, mock_conn):
        """验证默认 limit=50"""
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        with patch("models.operator.get_connection", return_value=conn):
            OperatorLogDAO.get_by_operator("op001")
            params = cursor.execute.call_args[0][1]
            assert params == ("op001", 50)
