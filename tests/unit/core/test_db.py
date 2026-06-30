# -*- coding: utf-8 -*-
"""测试 core/db.py — 统一数据库连接管理器"""
import os
import pytest
from unittest.mock import patch, MagicMock


# ── helpers ──

def _get_db_mod():
    import core.db as db_mod
    return db_mod


# ── fixtures ──

@pytest.fixture(autouse=True)
def reset_db():
    """每次测试前后重置 DB 单例 + 模块级 db._pool — 防止 pool 持有 mock 时的脏 cursorclass 跨测试污染"""
    db_mod = _get_db_mod()
    # setUp：清掉前一个测试可能残留的污染（最悲观：默认有污染）
    db_mod.DB._instance = None
    db_mod.ConnectionPool._instance = None
    if hasattr(db_mod.db, '_pool'):
        db_mod.db._pool = None
    yield
    # tearDown：清掉当前测试的污染，避免影响下一个测试
    db_mod.DB._instance = None
    db_mod.ConnectionPool._instance = None
    if hasattr(db_mod.db, '_pool'):
        db_mod.db._pool = None


@pytest.fixture
def mock_pymysql():
    """模拟 pymysql 模块"""
    db_mod = _get_db_mod()
    mock_mod = MagicMock()
    mock_mod.cursors.DictCursor = "DictCursor"
    with patch.object(db_mod, 'pymysql', mock_mod):
        yield mock_mod


@pytest.fixture
def db_with_pool(mock_pymysql):
    """初始化好的 DB（带 pymysql mock）"""
    db_mod = _get_db_mod()
    db_mod.db._do_init()
    return db_mod.db


# ── 单例 ──

class TestSingleton:
    def test_db_is_singleton(self, mock_pymysql):
        db_mod = _get_db_mod()
        a = db_mod.DB()
        b = db_mod.DB()
        assert a is b

    def test_pool_is_singleton(self, mock_pymysql):
        db_mod = _get_db_mod()
        a = db_mod.ConnectionPool()
        b = db_mod.ConnectionPool()
        assert a is b

    def test_db_init(self, mock_pymysql):
        db_mod = _get_db_mod()
        db_mod.DB._instance = None
        db_mod.ConnectionPool._instance = None
        db_mod.DB.init()
        assert db_mod.DB._instance is not None


# ── 连接池 ──

class TestConnectionPool:
    def test_init(self, mock_pymysql):
        db_mod = _get_db_mod()
        pool = db_mod.ConnectionPool()
        pool.init({"host": "127.0.0.1", "port": 3306, "pool_size": 5})
        assert pool._config is not None
        assert pool._max_size == 5

    def test_init_defaults(self, mock_pymysql):
        db_mod = _get_db_mod()
        pool = db_mod.ConnectionPool()
        pool.init()
        assert pool._max_size >= 2

    def test_get_creates_connection(self, mock_pymysql, db_with_pool):
        db_mod = _get_db_mod()
        pool = db_with_pool._pool
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn

        result = pool.get()
        mock_pymysql.connect.assert_called_once()
        assert isinstance(result, db_mod.PooledConnection)

    def test_get_reuses_connection(self, mock_pymysql, db_with_pool):
        db_mod = _get_db_mod()
        pool = db_with_pool._pool
        mock_conn = MagicMock()
        mock_conn.ping.return_value = None
        pool._pool.append(mock_conn)

        result = pool.get()
        mock_pymysql.connect.assert_not_called()
        assert isinstance(result, db_mod.PooledConnection)

    def test_get_bad_connection_fallback(self, mock_pymysql, db_with_pool):
        db_mod = _get_db_mod()
        pool = db_with_pool._pool
        bad = MagicMock()
        bad.ping.side_effect = Exception("gone")
        pool._pool.append(bad)

        good = MagicMock()
        mock_pymysql.connect.return_value = good

        result = pool.get()
        assert isinstance(result, db_mod.PooledConnection)
        mock_pymysql.connect.assert_called_once()

    def test_return_and_reuse(self, mock_pymysql, db_with_pool):
        pool = db_with_pool._pool
        raw = MagicMock()
        pool.return_connection(raw)
        assert len(pool._pool) == 1

    def test_return_full_pool_closes(self, mock_pymysql, db_with_pool):
        pool = db_with_pool._pool
        pool._pool = [MagicMock() for _ in range(pool._max_size)]
        raw = MagicMock()
        pool.return_connection(raw)
        raw.close.assert_called_once()

    def test_close_all(self, mock_pymysql, db_with_pool):
        pool = db_with_pool._pool
        raw = MagicMock()
        pool._pool = [raw]
        pool.close_all()
        raw.close.assert_called_once()
        assert len(pool._pool) == 0


# ── PooledConnection ──

class TestPooledConnection:
    def test_close_returns_to_pool(self, mock_pymysql, db_with_pool):
        db_mod = _get_db_mod()
        pool = db_with_pool._pool
        raw = MagicMock()
        initial = len(pool._pool)
        pc = db_mod.PooledConnection(pool, raw)
        pc.close()
        assert len(pool._pool) == initial + 1

    def test_getattr_delegates(self, mock_pymysql):
        db_mod = _get_db_mod()
        pool = MagicMock()
        raw = MagicMock()
        raw.foo = "bar"
        pc = db_mod.PooledConnection(pool, raw)
        assert pc.foo == "bar"

    def test_cursor_delegates(self, mock_pymysql):
        db_mod = _get_db_mod()
        pool = MagicMock()
        raw = MagicMock()
        pc = db_mod.PooledConnection(pool, raw)
        pc.cursor()
        raw.cursor.assert_called_once()

    def test_commit_delegates(self, mock_pymysql):
        db_mod = _get_db_mod()
        pool = MagicMock()
        raw = MagicMock()
        pc = db_mod.PooledConnection(pool, raw)
        pc.commit()
        raw.commit.assert_called_once()

    def test_rollback_delegates(self, mock_pymysql):
        db_mod = _get_db_mod()
        pool = MagicMock()
        raw = MagicMock()
        pc = db_mod.PooledConnection(pool, raw)
        pc.rollback()
        raw.rollback.assert_called_once()


# ── 配置读取 ──

class TestConfig:
    def test_config_defaults(self, monkeypatch):
        from core.db import _get_db_config
        monkeypatch.delenv("DB_HOST", raising=False)
        monkeypatch.delenv("MYSQL_HOST", raising=False)
        c = _get_db_config()
        assert c["host"] == "localhost"
        assert c["port"] == 3306

    def test_db_prefix_priority(self, monkeypatch):
        from core.db import _get_db_config
        monkeypatch.setenv("DB_HOST", "db.example.com")
        monkeypatch.setenv("MYSQL_HOST", "old.example.com")
        c = _get_db_config()
        assert c["host"] == "db.example.com"

    def test_mysql_fallback(self, monkeypatch):
        from core.db import _get_db_config
        monkeypatch.setenv("MYSQL_HOST", "mysql.example.com")
        monkeypatch.delenv("DB_HOST", raising=False)
        c = _get_db_config()
        assert c["host"] == "mysql.example.com"

    def test_pool_size_bounds(self, monkeypatch):
        from core.db import _get_db_config
        monkeypatch.setenv("DB_POOL_SIZE", "3")
        c = _get_db_config()
        assert c["pool_size"] == 3


# ── get_connection 兼容函数 ──

class TestBackwardCompat:
    def test_get_connection_returns_pooled(self, mock_pymysql, db_with_pool):
        from core.db import get_connection
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        conn = get_connection()
        assert conn is not None

    def test_get_connection_context(self, mock_pymysql, db_with_pool):
        from core.db import get_connection_context
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        with get_connection_context() as conn:
            assert conn is not None

    def test_legacy_imports_exist(self):
        from core.db import MySQLConnectionPool, PooledConnection, reload_db_config
        assert MySQLConnectionPool is not None
        assert PooledConnection is not None
        assert callable(reload_db_config)


# ── 便捷方法 ──

class TestConvenience:
    def test_execute_query(self, mock_pymysql, db_with_pool):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [{"id": 1}]
        mock_conn.cursor.return_value = mock_cur
        mock_pymysql.connect.return_value = mock_conn

        result = db_with_pool.execute_query("SELECT 1")
        assert result == [{"id": 1}]
        mock_cur.execute.assert_called_once_with("SELECT 1", ())

    def test_execute_update(self, mock_pymysql, db_with_pool):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.rowcount = 5
        mock_conn.cursor.return_value = mock_cur
        mock_pymysql.connect.return_value = mock_conn

        result = db_with_pool.execute_update("UPDATE foo SET x=1")
        assert result == 5

    def test_execute_insert(self, mock_pymysql, db_with_pool):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.lastrowid = 42
        mock_conn.cursor.return_value = mock_cur
        mock_pymysql.connect.return_value = mock_conn

        result = db_with_pool.execute_insert("INSERT INTO foo VALUES ()")
        assert result == 42

    def test_transaction_commits(self, mock_pymysql, db_with_pool):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_pymysql.connect.return_value = mock_conn

        with db_with_pool.transaction():
            pass
        # 验证底层连接 commit 被调用
        mock_conn.commit.assert_called_once()

    def test_transaction_rollback_on_error(self, mock_pymysql, db_with_pool):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_pymysql.connect.return_value = mock_conn

        with pytest.raises(ValueError):
            with db_with_pool.transaction():
                raise ValueError("boom")
        mock_conn.rollback.assert_called_once()


# ── 边界用例 ──

class TestEdgeCases:
    def test_get_connection_without_init_auto_inits(self, mock_pymysql):
        from core.db import get_connection
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        conn = get_connection()
        assert conn is not None

    def test_close_idempotent(self, mock_pymysql, db_with_pool):
        """多次 close 不抛异常"""
        db_with_pool.close()
        db_with_pool.close()  # 不应报错

    def test_reload_config(self, mock_pymysql, db_with_pool):
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn
        db_with_pool.reload_config()
        assert db_with_pool._pool is not None
