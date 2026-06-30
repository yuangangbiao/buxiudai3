# -*- coding: utf-8 -*-
"""
测试 models.operator 模块
覆盖 OperatorDAO / OperatorLogDAO 全部方法
"""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime

from models.operator import OperatorDAO, OperatorLogDAO


# ── 辅助函数 ─────────────────────────────────────────────

def make_row(d: dict) -> MagicMock:
    """创建模拟的数据库行，支持 dict(row) 转换"""
    row = MagicMock()
    row.__iter__.return_value = iter(d.items())
    row.keys.return_value = list(d.keys())
    return row


# ── Fixtures ─────────────────────────────────────────────

@pytest.fixture
def mock_conn():
    """模拟 get_connection → conn → cursor"""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# ── OperatorDAO.get_all ──────────────────────────────────

class TestOperatorDAOGetAll:
    """测试 OperatorDAO.get_all"""

    def test_returns_all_operators(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [
            {"id": 1, "operator_id": "001", "name": "张三", "role": "操作员"},
            {"id": 2, "operator_id": "002", "name": "李四", "role": "管理员"},
        ]
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.get_all()
            assert len(result) == 2
            assert result[0]["operator_id"] == "001"
            assert result[1]["name"] == "李四"
            cursor.execute.assert_called_once()
            conn.close.assert_called_once()

    def test_empty_result(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.get_all()
            assert result == []
            conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")
        with patch("models.operator.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OperatorDAO.get_all()
            conn.close.assert_called_once()


# ── OperatorDAO.get_by_id ────────────────────────────────

class TestOperatorDAOGetById:
    """测试 OperatorDAO.get_by_id"""

    def test_returns_operator(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = {"id": 1, "operator_id": "001", "name": "张三"}
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.get_by_id("001")
            assert result["operator_id"] == "001"
            assert result["name"] == "张三"
            conn.close.assert_called_once()

    def test_not_found(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.get_by_id("unknown")
            assert result is None
            conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")
        with patch("models.operator.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OperatorDAO.get_by_id("001")
            conn.close.assert_called_once()


# ── OperatorDAO.get_by_wechat_userid ─────────────────────

class TestOperatorDAOGetByWechat:
    """测试 OperatorDAO.get_by_wechat_userid"""

    def test_returns_operator(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = {"id": 1, "wechat_userid": "wx001", "name": "张三"}
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.get_by_wechat_userid("wx001")
            assert result["wechat_userid"] == "wx001"
            conn.close.assert_called_once()

    def test_returns_none_if_empty_userid(self):
        """空 userid 提前返回 None，不连接数据库"""
        result = OperatorDAO.get_by_wechat_userid("")
        assert result is None
        result = OperatorDAO.get_by_wechat_userid(None)
        assert result is None

    def test_not_found(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.get_by_wechat_userid("nonexistent")
            assert result is None
            conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")
        with patch("models.operator.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OperatorDAO.get_by_wechat_userid("wx001")
            conn.close.assert_called_once()


# ── OperatorDAO.login ────────────────────────────────────

class TestOperatorDAOLogin:
    """测试 OperatorDAO.login — 覆盖 4 条路径"""

    def test_user_not_found(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.login("001", "password")
            assert result is None
            # 由于 finally 块也有 conn.close()，加上第78行的 conn.close()
            assert conn.close.call_count == 2

    def test_no_salt_plain_match(self, mock_conn):
        """旧系统 — 无 salt，明文密码匹配"""
        conn, cursor = mock_conn
        row = {"id": 1, "operator_id": "001", "name": "张三",
               "role": "操作员", "status": "正常",
               "password": "plain123", "password_salt": None}
        cursor.fetchone.return_value = row

        # 模拟第二次连接
        conn2 = MagicMock()
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2

        with patch("models.operator.get_connection", side_effect=[conn, conn2]):
            with patch("models.operator.hash_password", return_value=("hashed", "newsalt")):
                result = OperatorDAO.login("001", "plain123")

                assert result["operator_id"] == "001"
                assert result["name"] == "张三"
                # 验证密码更新调用
                cursor2.execute.assert_called_once()
                conn2.commit.assert_called_once()
                assert conn.close.call_count == 2

    def test_no_salt_plain_mismatch(self, mock_conn):
        """旧系统 — 无 salt，明文密码不匹配"""
        conn, cursor = mock_conn
        row = {"id": 1, "operator_id": "001", "name": "张三",
               "role": "操作员", "status": "正常",
               "password": "plain123", "password_salt": None}
        cursor.fetchone.return_value = row
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.login("001", "wrong_password")
            assert result is None
            assert conn.close.call_count == 2

    def test_with_salt_correct(self, mock_conn):
        """新系统 — 有 salt，密码正确"""
        conn, cursor = mock_conn
        row = {"id": 1, "operator_id": "001", "name": "张三",
               "role": "操作员", "status": "正常",
               "password": "stored_hash", "password_salt": "mysalt"}
        cursor.fetchone.return_value = row

        conn2 = MagicMock()
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2

        with patch("models.operator.get_connection", side_effect=[conn, conn2]):
            with patch("models.operator.verify_password", return_value=True):
                result = OperatorDAO.login("001", "correct_pwd")

                assert result["operator_id"] == "001"
                # 验证 last_login 被更新
                cursor2_executed = cursor2.execute.call_args[0][0]
                assert "last_login" in cursor2_executed
                conn2.commit.assert_called_once()

    def test_with_salt_wrong(self, mock_conn):
        """新系统 — 有 salt，密码错误"""
        conn, cursor = mock_conn
        row = {"id": 1, "operator_id": "001", "name": "张三",
               "role": "操作员", "status": "正常",
               "password": "stored_hash", "password_salt": "mysalt"}
        cursor.fetchone.return_value = row
        with patch("models.operator.get_connection", return_value=conn):
            with patch("models.operator.verify_password", return_value=False):
                result = OperatorDAO.login("001", "wrong_pwd")
                assert result is None
                assert conn.close.call_count == 2

    def test_exception_closes_connection(self, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")
        with patch("models.operator.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OperatorDAO.login("001", "pwd")
            conn.close.assert_called_once()


# ── OperatorDAO.add ──────────────────────────────────────

class TestOperatorDAOAdd:
    """测试 OperatorDAO.add"""

    def test_add_with_wechat_userid(self, mock_conn):
        conn, cursor = mock_conn
        data = {"operator_id": "003", "name": "王五", "wechat_userid": "wx003"}
        with patch("models.operator.get_connection", return_value=conn):
            with patch("models.operator.hash_password", return_value=("hashed", "salt")):
                result = OperatorDAO.add(data)
                assert result is True
                cursor.execute.assert_called_once()
                sql = cursor.execute.call_args[0][0]
                assert "wechat_userid" in sql
                conn.commit.assert_called_once()
                conn.close.assert_called_once()

    def test_add_without_wechat_userid(self, mock_conn):
        conn, cursor = mock_conn
        data = {"operator_id": "004", "name": "赵六"}
        with patch("models.operator.get_connection", return_value=conn):
            with patch("models.operator.hash_password", return_value=("hashed", "salt")):
                result = OperatorDAO.add(data)
                assert result is True
                sql = cursor.execute.call_args[0][0]
                assert "wechat_userid" not in sql
                conn.commit.assert_called_once()
                conn.close.assert_called_once()

    def test_add_with_empty_wechat(self, mock_conn):
        """wechat_userid 为空字符串时等同于无"""
        conn, cursor = mock_conn
        data = {"operator_id": "005", "name": "钱七", "wechat_userid": ""}
        with patch("models.operator.get_connection", return_value=conn):
            with patch("models.operator.hash_password", return_value=("hashed", "salt")):
                result = OperatorDAO.add(data)
                assert result is True
                sql = cursor.execute.call_args[0][0]
                assert "wechat_userid" not in sql
                conn.close.assert_called_once()

    def test_add_default_role_and_status(self, mock_conn):
        """默认角色为操作员，状态为正常"""
        conn, cursor = mock_conn
        data = {"operator_id": "006", "name": "孙八"}
        with patch("models.operator.get_connection", return_value=conn):
            with patch("models.operator.hash_password", return_value=("hashed", "salt")):
                OperatorDAO.add(data)
                params = cursor.execute.call_args[0][1]
                assert "操作员" in params  # 默认 role
                assert "正常" in params    # 默认 status
                conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")
        with patch("models.operator.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OperatorDAO.add({"operator_id": "007", "name": "测试"})
            conn.close.assert_called_once()


# ── OperatorDAO.update ───────────────────────────────────

class TestOperatorDAOUpdate:
    """测试 OperatorDAO.update"""

    def test_update_name(self, mock_conn):
        conn, cursor = mock_conn
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.update("001", {"name": "新名字"})
            assert result is True
            sql = cursor.execute.call_args[0][0]
            assert "name=%s" in sql
            conn.commit.assert_called_once()
            conn.close.assert_called_once()

    def test_update_multiple_fields(self, mock_conn):
        conn, cursor = mock_conn
        data = {"name": "新名", "role": "管理员", "status": "停用"}
        with patch("models.operator.get_connection", return_value=conn):
            OperatorDAO.update("001", data)
            sql = cursor.execute.call_args[0][0]
            assert "name=%s" in sql
            assert "role=%s" in sql
            assert "status=%s" in sql
            assert "updated_at=%s" in sql
            params = cursor.execute.call_args[0][1]
            assert "停用" in params
            conn.close.assert_called_once()

    def test_update_password(self, mock_conn):
        conn, cursor = mock_conn
        data = {"password": "newpass"}
        with patch("models.operator.get_connection", return_value=conn):
            with patch("models.operator.hash_password", return_value=("h", "s")):
                OperatorDAO.update("001", data)
                sql = cursor.execute.call_args[0][0]
                assert "password=%s" in sql
                assert "password_salt=%s" in sql
                conn.close.assert_called_once()

    def test_update_wechat_userid(self, mock_conn):
        conn, cursor = mock_conn
        data = {"wechat_userid": "wx_new"}
        with patch("models.operator.get_connection", return_value=conn):
            OperatorDAO.update("001", data)
            sql = cursor.execute.call_args[0][0]
            assert "wechat_userid=%s" in sql
            conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")
        with patch("models.operator.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OperatorDAO.update("001", {"name": "测试"})
            conn.close.assert_called_once()


# ── OperatorDAO.delete ───────────────────────────────────

class TestOperatorDAODelete:
    """测试 OperatorDAO.delete"""

    def test_delete_operator(self, mock_conn):
        conn, cursor = mock_conn
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.delete("non_admin")
            assert result is True
            cursor.execute.assert_called_once()
            conn.commit.assert_called_once()
            conn.close.assert_called_once()

    def test_cannot_delete_admin(self):
        """不能删除管理员账户"""
        result = OperatorDAO.delete("admin")
        assert result is False

    def test_exception_closes_connection(self, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")
        with patch("models.operator.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OperatorDAO.delete("non_admin")
            conn.close.assert_called_once()


# ── OperatorDAO.change_password ──────────────────────────

class TestOperatorDAOChangePassword:
    """测试 OperatorDAO.change_password — 4 条路径"""

    def test_user_not_found(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchone.return_value = None
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.change_password("001", "old", "new")
            assert result is False
            # 第223行和252行各一个 close
            assert conn.close.call_count == 2

    def test_no_salt_old_match(self, mock_conn):
        """旧系统 — 无 salt，明文匹配"""
        conn, cursor = mock_conn
        row = {"password": "oldpass", "password_salt": None}
        cursor.fetchone.return_value = row

        conn2 = MagicMock()
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2

        with patch("models.operator.get_connection", side_effect=[conn, conn2]):
            with patch("models.operator.hash_password", return_value=("new_hash", "new_salt")):
                result = OperatorDAO.change_password("001", "oldpass", "newpass")
                assert result is True
                cursor2.execute.assert_called_once()
                conn2.commit.assert_called_once()

    def test_no_salt_old_mismatch(self, mock_conn):
        """旧系统 — 无 salt，明文不匹配"""
        conn, cursor = mock_conn
        row = {"password": "oldpass", "password_salt": None}
        cursor.fetchone.return_value = row
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorDAO.change_password("001", "wrong_old", "newpass")
            assert result is False
            assert conn.close.call_count == 2

    def test_with_salt_old_correct(self, mock_conn):
        """新系统 — 有 salt，旧密码正确"""
        conn, cursor = mock_conn
        row = {"password": "stored_hash", "password_salt": "salt"}
        cursor.fetchone.return_value = row

        conn2 = MagicMock()
        cursor2 = MagicMock()
        conn2.cursor.return_value = cursor2

        with patch("models.operator.get_connection", side_effect=[conn, conn2]):
            with patch("models.operator.verify_password", return_value=True):
                with patch("models.operator.hash_password", return_value=("new_hash", "new_salt")):
                    result = OperatorDAO.change_password("001", "oldpwd", "newpwd")
                    assert result is True
                    cursor2.execute.assert_called_once()
                    conn2.commit.assert_called_once()

    def test_with_salt_old_wrong(self, mock_conn):
        """新系统 — 有 salt，旧密码错误"""
        conn, cursor = mock_conn
        row = {"password": "stored_hash", "password_salt": "salt"}
        cursor.fetchone.return_value = row
        with patch("models.operator.get_connection", return_value=conn):
            with patch("models.operator.verify_password", return_value=False):
                result = OperatorDAO.change_password("001", "wrong_old", "newpwd")
                assert result is False
                assert conn.close.call_count == 2

    def test_exception_closes_connection(self, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")
        with patch("models.operator.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OperatorDAO.change_password("001", "old", "new")
            conn.close.assert_called_once()


# ── OperatorLogDAO.add ───────────────────────────────────

class TestOperatorLogDAOAdd:
    """测试 OperatorLogDAO.add"""

    def test_add_log(self, mock_conn):
        conn, cursor = mock_conn
        with patch("models.operator.get_connection", return_value=conn):
            OperatorLogDAO.add("001", "张三", "登录系统", "user", "001", "登录成功")
            cursor.execute.assert_called_once()
            conn.commit.assert_called_once()
            conn.close.assert_called_once()

    def test_add_log_minimal_params(self, mock_conn):
        """仅必填参数"""
        conn, cursor = mock_conn
        with patch("models.operator.get_connection", return_value=conn):
            OperatorLogDAO.add("002", "李四", "查询订单")
            sql = cursor.execute.call_args[0][0]
            assert "INSERT INTO operator_logs" in sql
            conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")
        with patch("models.operator.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OperatorLogDAO.add("001", "张三", "测试")
            conn.close.assert_called_once()


# ── OperatorLogDAO.get_logs ──────────────────────────────

class TestOperatorLogDAOGetLogs:
    """测试 OperatorLogDAO.get_logs"""

    def test_returns_logs(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [{"id": 1, "operator_id": "001", "action": "登录"}]
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorLogDAO.get_logs()
            assert len(result) == 1
            assert result[0]["action"] == "登录"
            conn.close.assert_called_once()

    def test_returns_logs_with_limit(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        with patch("models.operator.get_connection", return_value=conn):
            OperatorLogDAO.get_logs(limit=50)
            params = cursor.execute.call_args[0][1]
            assert params == (50,)
            conn.close.assert_called_once()

    def test_empty(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorLogDAO.get_logs()
            assert result == []
            conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")
        with patch("models.operator.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OperatorLogDAO.get_logs()
            conn.close.assert_called_once()


# ── OperatorLogDAO.get_by_operator ───────────────────────

class TestOperatorLogDAOGetByOperator:
    """测试 OperatorLogDAO.get_by_operator"""

    def test_returns_logs(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = [{"id": 1, "operator_id": "001", "action": "创建订单"}]
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorLogDAO.get_by_operator("001")
            assert len(result) == 1
            assert result[0]["action"] == "创建订单"
            conn.close.assert_called_once()

    def test_with_custom_limit(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        with patch("models.operator.get_connection", return_value=conn):
            OperatorLogDAO.get_by_operator("001", limit=10)
            params = cursor.execute.call_args[0][1]
            assert params == ("001", 10)
            conn.close.assert_called_once()

    def test_empty(self, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []
        with patch("models.operator.get_connection", return_value=conn):
            result = OperatorLogDAO.get_by_operator("nonexistent")
            assert result == []
            conn.close.assert_called_once()

    def test_exception_closes_connection(self, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB error")
        with patch("models.operator.get_connection", return_value=conn):
            with pytest.raises(Exception, match="DB error"):
                OperatorLogDAO.get_by_operator("001")
            conn.close.assert_called_once()
