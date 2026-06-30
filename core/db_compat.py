"""core/db_compat.py - pymysql.connect 兼容层（彻底重构版）

[T1-T5 2026-06-14] 业务代码 1 行替换，走连接池

[T7 修复 2026-06-14] 修复 DictCursor 兼容问题
之前：shim 用 MySQLStorage 的 pool (DictCursor) → 业务 cur.fetchone()[0] 报 KeyError
现在：shim 创建自己的连接池 (tuple cursor)，与 pymysql.connect 默认行为一致
      业务显式 cur = conn.cursor(pymysql.cursors.DictCursor) 拿 dict

[T8 修复 2026-06-17] 支持多数据库连接池
之前：_get_pool() 硬编码 CONTAINER_MYSQL_CFG，get_conn(**STEELBELT_MYSQL_CFG) 被忽略
现在：按 (host:port/database) 键值管理多池，get_conn 的参数真正生效
"""
import logging
import pymysql
from dbutils.pooled_db import PooledDB
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT

logger = logging.getLogger(__name__)

# 多数据库连接池，键 = "host:port/database"
_POOLS = {}

_DEFAULT_CFG = CONTAINER_MYSQL_CFG


def _pool_key(**cfg) -> str:
    return f"{cfg.get('host', 'localhost')}:{cfg.get('port', 3306)}/{cfg.get('database', '')}"


def _get_pool(**cfg):
    if not cfg:
        cfg = _DEFAULT_CFG
    key = _pool_key(**cfg)
    if key not in _POOLS:
        _POOLS[key] = PooledDB(
            creator=pymysql,
            maxconnections=50, mincached=5, maxcached=15,
            blocking=True, ping=1,
            **cfg, connect_timeout=DB_CONNECT_TIMEOUT, autocommit=True,
        )
    return _POOLS[key]


def get_conn(**cfg):
    """pymysql.connect 兼容版，走连接池

    支持多数据库：按 host:port/database 自动管理多连接池。
    无参数时默认使用 CONTAINER_MYSQL_CFG。

    Returns:
        _PooledConnShim: 包装 pymysql 连接，commit/rollback/close 全部支持
    """
    return _PooledConnShim(**cfg)


class _PooledConnShim:
    """pymysql 连接 兼容包装，底层走连接池

    [T7] 默认 cursor = tuple (pymysql 默认)，不是 DictCursor
    业务层显式 cur = conn.cursor(pymysql.cursors.DictCursor) 拿 dict
    """

    def __init__(self, **cfg):
        self._pooled = _get_pool(**cfg).connection()

    def cursor(self, *args, **kwargs):
        """透传 cursor class，调用方可用 pymysql.cursors.DictCursor"""
        return self._pooled.cursor(*args, **kwargs)

    def commit(self):
        return self._pooled.commit()

    def rollback(self):
        return self._pooled.rollback()

    def close(self):
        try:
            return self._pooled.close()
        except Exception:
            return

    def __enter__(self):
        return self, self._pooled.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                self._pooled.commit()
            else:
                try:
                    self._pooled.rollback()
                except Exception as e:
                    logger.warning(f"[DB] 回滚失败: {e}")
        finally:
            try:
                self._pooled.close()
            except Exception as e:
                logger.warning(f"[DB] 关闭连接失败: {e}")
        return False
