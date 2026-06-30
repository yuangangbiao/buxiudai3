"""core/db_compat.py - 统一路由到 _db_pools（悲观审计 Round4 重构）

之前：独立管理 PooledDB 多数据库连接池（功能与 _db_pools 重复）
现在：简单 shim，路由到 _db_pools
"""

import logging

logger = logging.getLogger(__name__)


def get_conn(**cfg):
    """pymysql.connect 兼容版，统一路由到 _db_pools

    支持多数据库：按 host:port/database 自动路由到对应连接池。
    无参数时默认使用 container 数据库。

    Returns:
        pymysql.connections.Connection: 来自 _db_pools 的连接
    """
    db = cfg.get("database", "")
    try:
        from core._db_pools import get_container_connection, get_steel_belt_connection

        if db == "steel_belt":
            return get_steel_belt_connection(autocommit=True)
        else:
            return get_container_connection(autocommit=True)
    except Exception:
        logger.warning("[db_compat] _db_pools 不可用，回退直连")
        import pymysql
        from core.config import CONTAINER_MYSQL_CFG

        return pymysql.connect(**(cfg or CONTAINER_MYSQL_CFG))
