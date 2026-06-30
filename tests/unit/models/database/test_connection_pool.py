# -*- coding: utf-8 -*-
"""
测试 models/database/connection_pool.py（历史归档，2026-06-09 起跳过）

模块已归档到 _archive/legacy_db/connection_pool.py，保留本测试文件作为
历史回归参考。所有用例已标记为 skip，不会影响 CI。

恢复方式（如需重新启用）：
    1. 将 _archive/legacy_db/connection_pool.py 移回 models/database/
    2. 删除本文件顶部的 pytestmark skip 标记
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import importlib

# 历史归档：所有用例统一跳过
pytestmark = pytest.mark.skip(
    reason="models/database/connection_pool.py 已归档到 _archive/legacy_db/，"
           "由 core.db.ConnectionPool 替代。"
)


# ============================================================
# fixtures
# ============================================================

@pytest.fixture(autouse=True)
def reset_pool():
    """每次测试后重置全局 _mysql_pool，避免测试间互相影响"""
    import models.database.connection_pool as cp
    cp._mysql_pool = None
    if hasattr(cp.MySQLConnectionPool, '_instance'):
        cp.MySQLConnectionPool._instance = None
    yield
    cp._mysql_pool = None
    cp.MySQLConnectionPool._instance = None


@pytest.fixture
def mock_pymysql():
    """模拟 pymysql 模块 — 直接替换 connection_pool 模块中的引用"""
    import models.database.connection_pool as cp
    mock_mod = MagicMock()
    mock_mod.cursors.DictCursor = "DictCursor"
    with patch.object(cp, 'pymysql', mock_mod):
        yield mock_mod


@pytest.fixture
def mock_no_pymysql():
    """模拟 pymysql 不可用"""
    with patch.dict('sys.modules', {'pymysql': None}):
        # 强制重载 module 触发 import 分支
        import importlib
        import models.database.connection_pool as cp
        importlib.reload(cp)
        yield cp
    # 重新加载恢复 pymysql
    importlib.reload(cp)


@pytest.fixture
def fresh_pool_module():
    """返回一个干净导入的连接池模块引用"""
    import models.database.connection_pool as cp
    return cp


# ============================================================
# 测试模块级初始化和 pymysql 回退
# ============================================================

class TestModuleInit:
    """测试模块级的 pymysql 导入处理"""

    def test_pymysql_imported_by_default(self, fresh_pool_module):
        """默认情况下 pymysql 可用"""
        import pymysql
        assert fresh_pool_module.pymysql is pymysql

    def test_pymysql_none_when_missing(self):
        """pymysql 不可用时模块变量为 None（子进程方式）"""
        import subprocess
        import tempfile
        here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))))
        script = textwrap.dedent("""\
        import sys
        sys.modules['pymysql'] = None
        # 清除已有缓存
        for k in list(sys.modules.keys()):
            if 'connection_pool' in k:
                del sys.modules[k]
        import importlib
        import models.database.connection_pool as cp
        importlib.reload(cp)
        print(type(cp.pymysql).__name__)
        """)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False,
                                         encoding="utf-8") as f:
            f.write(script)
            tmppath = f.name
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = here + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run(
                [sys.executable, tmppath],
                capture_output=True, text=True, timeout=10,
                env=env,
            )
        finally:
            try:
                os.unlink(tmppath)
            except OSError:
                pass
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert result.stdout.strip() == "NoneType"


# ============================================================
# 测试 MySQLConnectionPool 单例
# ============================================================

class TestMySQLConnectionPoolSingleton:
    """测试 MySQLConnectionPool 单例模式"""

    def test_singleton(self, fresh_pool_module):
        """两次实例化返回同一对象"""
        p1 = fresh_pool_module.MySQLConnectionPool()
        p2 = fresh_pool_module.MySQLConnectionPool()
        assert p1 is p2

    def test_default_pool_size(self, fresh_pool_module):
        """默认连接池大小 20"""
        pool = fresh_pool_module.MySQLConnectionPool()
        assert pool._max_connections == 20

    def test_min_pool_size(self, fresh_pool_module, monkeypatch):
        """最小连接池大小为 5"""
        monkeypatch.setenv("MYSQL_POOL_SIZE", "1")
        # 重新实例化（单例，需要重置）
        fresh_pool_module.MySQLConnectionPool._instance = None
        pool = fresh_pool_module.MySQLConnectionPool()
        assert pool._max_connections == 5

    def test_max_pool_size(self, fresh_pool_module, monkeypatch):
        """最大连接池大小为 100"""
        monkeypatch.setenv("MYSQL_POOL_SIZE", "200")
        fresh_pool_module.MySQLConnectionPool._instance = None
        pool = fresh_pool_module.MySQLConnectionPool()
        assert pool._max_connections == 100

    def test_pool_size_from_env(self, fresh_pool_module, monkeypatch):
        """从环境变量读取连接池大小"""
        monkeypatch.setenv("MYSQL_POOL_SIZE", "15")
        fresh_pool_module.MySQLConnectionPool._instance = None
        pool = fresh_pool_module.MySQLConnectionPool()
        assert pool._max_connections == 15


# ============================================================
# 测试 init / get_connection / get_pooled_connection
# ============================================================

class TestPoolOperations:
    """测试连接池核心操作"""

    def test_init_sets_cursorclass(self, fresh_pool_module, mock_pymysql):
        """init 设置 cursorclass"""
        pool = fresh_pool_module.MySQLConnectionPool()
        config = {"host": "localhost", "port": 3306}
        pool.init(config)
        assert pool._config["cursorclass"] == "DictCursor"

    def test_get_connection_returns_none_when_no_config(self, fresh_pool_module):
        """_config 为 None 时 get_connection 返回 None"""
        pool = fresh_pool_module.MySQLConnectionPool()
        assert pool._config is None
        assert pool.get_connection() is None

    def test_get_connection_creates_new(self, fresh_pool_module, mock_pymysql):
        """池空时创建新连接"""
        pool = fresh_pool_module.MySQLConnectionPool()
        pool.init({"host": "localhost", "port": 3306})
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        conn = pool.get_connection()
        assert conn is mock_conn
        mock_pymysql.connect.assert_called_once()

    def test_get_connection_reuses_existing(self, fresh_pool_module, mock_pymysql):
        """池中有连接时复用"""
        pool = fresh_pool_module.MySQLConnectionPool()
        pool.init({"host": "localhost", "port": 3306})
        mock_conn = MagicMock()
        pool._pool.append(mock_conn)
        conn = pool.get_connection()
        assert conn is mock_conn
        mock_conn.ping.assert_called_once_with(reconnect=True)

    def test_get_connection_fallback_on_ping_fail(self, fresh_pool_module, mock_pymysql):
        """ping 失败时自动创建新连接"""
        pool = fresh_pool_module.MySQLConnectionPool()
        pool.init({"host": "localhost", "port": 3306})
        bad_conn = MagicMock()
        bad_conn.ping.side_effect = Exception("连接断开")
        pool._pool.append(bad_conn)
        good_conn = MagicMock()
        mock_pymysql.connect.return_value = good_conn
        conn = pool.get_connection()
        assert conn is good_conn
        assert len(pool._pool) == 0  # 坏连接已被弹出

    def test_get_pooled_connection_no_config(self, fresh_pool_module):
        """_config 为 None 时 get_pooled_connection 返回 (None, False)"""
        pool = fresh_pool_module.MySQLConnectionPool()
        result, is_new = pool.get_pooled_connection()
        assert result is None
        assert is_new is False

    def test_get_pooled_connection_from_pool(self, fresh_pool_module, mock_pymysql):
        """池中有连接时返回 (conn, False)"""
        pool = fresh_pool_module.MySQLConnectionPool()
        pool.init({"host": "localhost", "port": 3306})
        mock_conn = MagicMock()
        pool._pool.append(mock_conn)
        conn, is_new = pool.get_pooled_connection()
        assert conn is mock_conn
        assert is_new is False

    def test_get_pooled_connection_new(self, fresh_pool_module, mock_pymysql):
        """池空时创建新连接返回 (conn, True)"""
        pool = fresh_pool_module.MySQLConnectionPool()
        pool.init({"host": "localhost", "port": 3306})
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        conn, is_new = pool.get_pooled_connection()
        assert conn is mock_conn
        assert is_new is True

    def test_get_pooled_connection_fallback(self, fresh_pool_module, mock_pymysql):
        """池中连接 ping 失败时创建新连接"""
        pool = fresh_pool_module.MySQLConnectionPool()
        pool.init({"host": "localhost", "port": 3306})
        bad_conn = MagicMock()
        bad_conn.ping.side_effect = Exception("断连")
        pool._pool.append(bad_conn)
        good_conn = MagicMock()
        mock_pymysql.connect.return_value = good_conn
        conn, is_new = pool.get_pooled_connection()
        assert conn is good_conn
        assert is_new is True


# ============================================================
# 测试 return_connection / close_all
# ============================================================

class TestPoolMaintenance:
    """测试连接归还和清理"""

    def test_return_none(self, fresh_pool_module):
        """归还 None 连接不做任何操作"""
        pool = fresh_pool_module.MySQLConnectionPool()
        pool.return_connection(None)
        assert len(pool._pool) == 0

    def test_return_connection(self, fresh_pool_module, mock_pymysql):
        """归还连接回池"""
        pool = fresh_pool_module.MySQLConnectionPool()
        pool._max_connections = 20
        mock_conn = MagicMock()
        pool.return_connection(mock_conn)
        assert len(pool._pool) == 1
        assert pool._pool[0] is mock_conn

    def test_return_when_pool_full(self, fresh_pool_module, mock_pymysql):
        """池满时关闭连接"""
        pool = fresh_pool_module.MySQLConnectionPool()
        pool._max_connections = 0  # 池满
        mock_conn = MagicMock()
        pool.return_connection(mock_conn)
        assert len(pool._pool) == 0
        mock_conn.close.assert_called_once()

    def test_return_ping_fail_then_close(self, fresh_pool_module, mock_pymysql):
        """ping 失败时关闭连接"""
        pool = fresh_pool_module.MySQLConnectionPool()
        pool._max_connections = 20
        mock_conn = MagicMock()
        mock_conn.ping.side_effect = Exception("断连")
        pool.return_connection(mock_conn)
        assert len(pool._pool) == 0
        mock_conn.close.assert_called_once()

    def test_return_full_ping_fail_close_fail(self, fresh_pool_module, mock_pymysql):
        """池满+ping失败+close失败，异常被吞掉"""
        pool = fresh_pool_module.MySQLConnectionPool()
        pool._max_connections = 0
        mock_conn = MagicMock()
        mock_conn.close.side_effect = Exception("关闭失败")
        # 不应抛出异常
        pool.return_connection(mock_conn)
        assert len(pool._pool) == 0

    def test_close_all(self, fresh_pool_module, mock_pymysql):
        """关闭所有连接并清空池"""
        pool = fresh_pool_module.MySQLConnectionPool()
        conns = [MagicMock() for _ in range(3)]
        pool._pool = conns[:]
        pool.close_all()
        assert len(pool._pool) == 0
        for c in conns:
            c.close.assert_called_once()

    def test_close_all_partial_failure(self, fresh_pool_module, mock_pymysql):
        """关闭连接时个别失败不影响其他"""
        pool = fresh_pool_module.MySQLConnectionPool()
        ok_conn = MagicMock()
        bad_conn = MagicMock()
        bad_conn.close.side_effect = Exception("关闭失败")
        pool._pool = [ok_conn, bad_conn]
        pool.close_all()
        assert len(pool._pool) == 0
        ok_conn.close.assert_called_once()
        bad_conn.close.assert_called_once()


# ============================================================
# 测试 PooledConnection
# ============================================================

class TestPooledConnection:
    """测试 PooledConnection 代理类"""

    def test_getattr_delegates(self, fresh_pool_module):
        """属性访问委托给内部连接"""
        mock_conn = MagicMock()
        pc = fresh_pool_module.PooledConnection(None, mock_conn)
        result = pc.some_attr
        # __getattr__ 返回 getattr(self._conn, name)，即 mock_conn.some_attr
        assert result is getattr(mock_conn, "some_attr")

    def test_close_returns_to_pool(self, fresh_pool_module):
        """close 时归还到池"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        pc = fresh_pool_module.PooledConnection(mock_pool, mock_conn)
        pc.close()
        mock_pool.return_connection.assert_called_once_with(mock_conn)

    def test_cursor_delegates(self, fresh_pool_module):
        """cursor 委托给内部连接"""
        mock_conn = MagicMock()
        pc = fresh_pool_module.PooledConnection(None, mock_conn)
        pc.cursor()
        mock_conn.cursor.assert_called_once()

    def test_cursor_with_kwargs(self, fresh_pool_module):
        """cursor 可以传递关键字参数"""
        mock_conn = MagicMock()
        pc = fresh_pool_module.PooledConnection(None, mock_conn)
        pc.cursor(dictionary=True)
        mock_conn.cursor.assert_called_once_with(dictionary=True)

    def test_commit_delegates(self, fresh_pool_module):
        """commit 委托给内部连接"""
        mock_conn = MagicMock()
        pc = fresh_pool_module.PooledConnection(None, mock_conn)
        pc.commit()
        mock_conn.commit.assert_called_once()

    def test_rollback_delegates(self, fresh_pool_module):
        """rollback 委托给内部连接"""
        mock_conn = MagicMock()
        pc = fresh_pool_module.PooledConnection(None, mock_conn)
        pc.rollback()
        mock_conn.rollback.assert_called_once()


# ============================================================
# 测试模块级函数
# ============================================================

class TestModuleFunctions:
    """测试 _get_mysql_pool / _cleanup_mysql_pool / _create_connection / get_connection_context / reload_db_config"""

    def test_get_mysql_pool_creates_and_inits(self, fresh_pool_module, mock_pymysql):
        """_get_mysql_pool 创建并初始化连接池"""
        pool = fresh_pool_module._get_mysql_pool()
        assert pool is not None
        assert pool._config is not None

    def test_get_mysql_pool_is_singleton(self, fresh_pool_module, mock_pymysql):
        """_get_mysql_pool 返回同一实例"""
        p1 = fresh_pool_module._get_mysql_pool()
        p2 = fresh_pool_module._get_mysql_pool()
        assert p1 is p2

    def test_get_mysql_pool_no_pymysql(self, fresh_pool_module, mock_pymysql):
        """有 pymysql 时 init 会被调用"""
        pool = fresh_pool_module._get_mysql_pool()
        assert pool._config is not None

    def test_cleanup_mysql_pool(self, fresh_pool_module, mock_pymysql):
        """_cleanup_mysql_pool 清理全局池"""
        import models.database.connection_pool as cp
        pool = cp._get_mysql_pool()
        cp._cleanup_mysql_pool()
        assert cp._mysql_pool is None

    def test_cleanup_mysql_pool_no_pool(self, fresh_pool_module, mock_pymysql):
        """没有连接池时 _cleanup_mysql_pool 不报错"""
        import models.database.connection_pool as cp
        cp._mysql_pool = None
        cp._cleanup_mysql_pool()
        # 不应抛出异常

    def test_create_connection(self, fresh_pool_module, mock_pymysql):
        """_create_connection 返回 PooledConnection"""
        import models.database.connection_pool as cp
        # mock pymysql.connect 返回有效连接
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        result = cp._create_connection()
        assert isinstance(result, cp.PooledConnection)

    def test_create_connection_no_pymysql(self):
        """pymysql=None 时 _create_connection 抛出异常"""
        # 用子进程测试
        import subprocess
        import tempfile
        import textwrap
        here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))))
        script = textwrap.dedent("""\
        import sys
        sys.modules['pymysql'] = None
        for k in list(sys.modules.keys()):
            if 'connection_pool' in k:
                del sys.modules[k]
        import importlib
        import models.database.connection_pool as cp
        importlib.reload(cp)
        try:
            cp._create_connection()
            print("NO_EXCEPTION")
        except Exception as e:
            print(str(e))
        """)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False,
                                         encoding="utf-8") as f:
            f.write(script)
            tmppath = f.name
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = here + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run(
                [sys.executable, tmppath],
                capture_output=True, text=True, timeout=10, env=env,
            )
        finally:
            try:
                os.unlink(tmppath)
            except OSError:
                pass
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "pymysql模块未安装" in result.stdout

    def test_get_connection_delegates(self, fresh_pool_module, mock_pymysql):
        """get_connection 函数委托给 _create_connection"""
        import models.database.connection_pool as cp
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        conn = cp.get_connection()
        assert isinstance(conn, cp.PooledConnection)

    def test_get_connection_context(self, fresh_pool_module, mock_pymysql):
        """get_connection_context 上下文管理器"""
        import models.database.connection_pool as cp
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        with cp.get_connection_context() as conn:
            assert isinstance(conn, cp.PooledConnection)
        # 退出上下文后 close 被调用，close 内部触发 return_connection → conn.ping
        assert mock_conn.ping.called

    def test_reload_db_config(self, fresh_pool_module, mock_pymysql):
        """reload_db_config 重新加载配置"""
        import models.database.connection_pool as cp
        import models.database.config as config
        old_config = config.MYSQL_CONFIG.copy()
        cp._get_mysql_pool()  # 确保池已创建
        cp.reload_db_config()
        # 验证重新加载
        assert cp._mysql_pool is not None
        assert cp._mysql_pool._config is not None

    def test_get_connection_is_new(self, fresh_pool_module, mock_pymysql):
        """get_connection 传 is_new=True 时记录日志"""
        import models.database.connection_pool as cp
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        with patch.object(cp.logger, 'info') as mock_info:
            conn = cp.MySQLConnectionPool()
            conn.init({"host": "localhost", "port": 3306})
            result = conn.get_connection(is_new=True)
        assert result is mock_conn
        mock_info.assert_any_call("[DB] MySQL连接成功")

    def test_create_connection_no_pool_result(self, fresh_pool_module, mock_pymysql):
        """_create_connection 在池返回空连接时抛出异常"""
        import models.database.connection_pool as cp
        mock_pool = MagicMock()
        mock_pool.get_pooled_connection.return_value = (None, False)
        with patch('models.database.connection_pool._get_mysql_pool', return_value=mock_pool):
            with pytest.raises(Exception, match="连接池返回空连接"):
                cp._create_connection()

    def test_create_connection_no_pymysql_inline(self, fresh_pool_module, mock_pymysql):
        """_create_connection 在 pymysql=None 时抛出异常（进程内）"""
        import models.database.connection_pool as cp
        with patch.object(cp, 'pymysql', None):
            with pytest.raises(Exception, match="pymysql模块未安装"):
                cp._create_connection()


# ============================================================
# 辅助
# ============================================================
import textwrap
