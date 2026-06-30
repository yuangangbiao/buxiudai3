# -*- coding: utf-8 -*-
"""
统一数据库连接管理器 (v3.0)

所有数据库操作唯一入口，替代:
  - core/database.py::DatabaseManager
  - models/database/_database_legacy.py 中的重复连接池类
  - 遍布项目的裸 pymysql.connect()

设计原则:
  1. 连接池统一管理，禁止即用即抛
  2. MySQL 为主，SQLite 保留开发/离线模式
  3. 完全向后兼容 models.database.get_connection() 调用者
  4. 环境变量: DB_* 优先，MYSQL_* 作为回退
"""
import os
import logging
import threading
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple

from utils.auto_schema import SafeCursor

logger = logging.getLogger(__name__)

# ── SQLite 仅在需要时加载 ──
_sqlite3: Any = None


def _get_sqlite3():
    global _sqlite3
    if _sqlite3 is None:
        import sqlite3 as _s
        _sqlite3 = _s
    return _sqlite3


# ── 配置获取 ──
def _get_db_config():
    """统一数据库配置读取，DB_* 环境变量优先，MYSQL_* 作为回退"""
    return {
        "host": os.getenv("DB_HOST", os.getenv("MYSQL_HOST", "localhost")),
        "port": int(os.getenv("DB_PORT", os.getenv("MYSQL_PORT", "3306"))),
        "user": os.getenv("DB_USER", os.getenv("MYSQL_USER", "root")),
        "password": os.getenv("DB_PASSWORD", os.getenv("MYSQL_PASSWORD", "")),
        "database": os.getenv("DB_NAME", os.getenv("MYSQL_DATABASE", "steel_belt")),
        "charset": os.getenv("DB_CHARSET", os.getenv("MYSQL_CHARSET", "utf8mb4")),
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", os.getenv("CONNECTION_TIMEOUT", "10"))),
        "pool_size": int(os.getenv("DB_POOL_SIZE", os.getenv("MYSQL_POOL_SIZE", "10"))),
    }


# ── 连接池 ──

try:
    import pymysql
except ImportError:
    pymysql = None


class ConnectionPool:
    """MySQL 连接池（单例）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._pool = []
                    obj._config = None
                    obj._max_size = 10
                    obj._min_size = 2
                    cls._instance = obj
        return cls._instance

    def init(self, config: dict = None):
        if config is None:
            config = _get_db_config()
        pool_size = config.pop("pool_size", 10)
        if pool_size < 2:
            pool_size = 2
        elif pool_size > 50:
            pool_size = 50
        self._max_size = pool_size
        self._min_size = min(2, pool_size)
        # 构建 pymysql 连接配置（排除非连接参数）
        self._config = {}
        for k, v in config.items():
            if k not in ("pool_size",):
                self._config[k] = v
        self._config["cursorclass"] = pymysql.cursors.DictCursor
        logger.info("[DB] 连接池初始化: max=%d", self._max_size)

    def get(self) -> "PooledConnection":
        """获取连接（始终返回 PooledConnection）"""
        if not self._config or not pymysql:
            raise RuntimeError("[DB] 连接池未初始化或 pymysql 未安装")
        # 尝试从池中复用
        while self._pool:
            conn = self._pool.pop()
            try:
                conn.ping(reconnect=True)
                return PooledConnection(self, conn)
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
        # 池空，创建新连接
        config = self._config.copy()
        raw = pymysql.connect(**config)
        return PooledConnection(self, raw)

    def return_connection(self, raw_conn):
        """归还连接"""
        if raw_conn is None:
            return
        if len(self._pool) < self._max_size:
            try:
                raw_conn.ping(reconnect=True)
                self._pool.append(raw_conn)
                return
            except Exception:
                pass
        try:
            raw_conn.close()
        except Exception:
            pass

    def close_all(self):
        for conn in self._pool:
            try:
                conn.close()
            except Exception:
                pass
        self._pool.clear()
        logger.info("[DB] 连接池已关闭")


class PooledConnection:
    """包装 MySQL 连接，close() 归还池而非真关闭"""

    def __init__(self, pool: ConnectionPool, conn):
        self._pool = pool
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        self._pool.return_connection(self._conn)

    def cursor(self, **kwargs):
        return self._conn.cursor(**kwargs)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()


# ── 统一管理器 ──

class DB:
    """统一数据库管理器（单例）"""

    _instance: Optional["DB"] = None
    _lock = threading.Lock()

    @classmethod
    def init(cls, config: dict = None):
        """显式初始化（通常在 app.py 启动时调用一次）"""
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls._instance._initialized = False
            cls._instance.__init__()
        cls._instance._do_init(config)

    def __new__(cls):
        if cls._instance is not None:
            return cls._instance
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._pool: Optional[ConnectionPool] = None
        self._sqlite_conn = None
        self._config: dict = {}

    def _do_init(self, config: dict = None):
        """实际初始化"""
        if not pymysql:
            logger.warning("[DB] pymysql 未安装，仅支持 SQLite 模式")
        else:
            self._pool = ConnectionPool()
            self._pool.init(config)

    def _is_sqlite(self) -> bool:
        return os.getenv("USE_SQLITE", "").lower() == "true"

    def get_connection(self):
        """获取数据库连接"""
        if self._is_sqlite():
            return self._get_sqlite_connection()
        if self._pool is None:
            self._do_init()
        return self._pool.get()

    def _get_sqlite_connection(self):
        if self._sqlite_conn is None:
            sq = _get_sqlite3()
            db_path = os.getenv(
                "SQLITE_PATH",
                os.path.join(os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data")), "app.db"),
            )
            db_path = os.path.abspath(db_path)
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            self._sqlite_conn = sq.connect(db_path, check_same_thread=False)
            self._sqlite_conn.row_factory = sq.Row
            logger.info("[DB] SQLite 连接: %s", db_path)
        return self._sqlite_conn

    # ── 便捷方法 ──

    @contextmanager
    def cursor(self, commit: bool = True):
        """上下文管理器: with db.cursor() as cur:"""
        conn = self.get_connection()
        cur = None
        try:
            cur = conn.cursor()
            yield cur
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if cur:
                cur.close()
            if not self._is_sqlite():
                conn.close()

    def execute_query(self, sql: str, params: tuple = None) -> List[Dict]:
        with self.cursor(commit=False) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

    def execute_update(self, sql: str, params: tuple = None) -> int:
        with self.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.rowcount

    def execute_insert(self, sql: str, params: tuple = None) -> int:
        with self.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.lastrowid

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close(self):
        if self._pool:
            self._pool.close_all()
        if self._sqlite_conn:
            self._sqlite_conn.close()
            self._sqlite_conn = None

    def reload_config(self, config: dict = None):
        """重新加载配置（热更新）"""
        if self._pool:
            self._pool.close_all()
        self._pool = None
        self._do_init(config)
        logger.info("[DB] 配置已重新加载")


# ── 全局单例 ──
db = DB()


# ── 向后兼容导出 ──
def get_connection():
    """获取数据库连接 — 兼容 models.database.get_connection 调用者"""
    return db.get_connection()


def get_direct_connection(**kwargs):
    """获取直接连接（自定义参数，不走环境变量配置）
    
    用于连接测试、临时诊断等需要自定义连接参数的场景。
    返回 PooledConnection，close() 时归还池。
    """
    if not pymysql:
        raise RuntimeError("[DB] pymysql 未安装")
    config = dict(kwargs)
    config.setdefault("charset", "utf8mb4")
    config.setdefault("cursorclass", pymysql.cursors.DictCursor)
    raw = pymysql.connect(**config)
    # 用独立连接池实例管理这些连接的回收
    pool = db._pool if db._pool else ConnectionPool()
    return PooledConnection(pool, raw)


@contextmanager
def get_connection_context():
    """上下文管理器版 — 兼容旧代码"""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def reload_db_config():
    """重新加载数据库配置 — 兼容旧代码"""
    db.reload_config()


@contextmanager
def get_db_cursor():
    """
    数据库操作的统一入口（自动集成 SafeCursor，支持自动建表）

    使用方式:
        with get_db_cursor() as (cursor, conn):
            cursor.execute("SELECT ...")
            conn.commit()

    cursor 已被 SafeCursor 包装，INSERT/UPDATE 时自动检测表结构，
    若表或字段不存在则自动创建。
    """
    conn = db.get_connection()
    cur = None
    try:
        cur = conn.cursor()
        safe_cursor = SafeCursor(cur, conn)
        yield safe_cursor, conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"[DB] 操作失败: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if not db._is_sqlite():
            conn.close()


# 保留旧类名引用，方便渐进迁移
MySQLConnectionPool = ConnectionPool
# PooledConnection 已在上面定义
