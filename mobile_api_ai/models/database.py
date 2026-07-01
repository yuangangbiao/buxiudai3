# -*- coding: utf-8 -*-
"""MySQL连接管理器 — 已迁移到 core.db 统一入口"""

from contextlib import contextmanager
from core.db import get_direct_connection, PooledConnection
from core.config import CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT


@contextmanager
def get_connection_context():
    conn = get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
    try:
        yield conn
    finally:
        conn.close()


def get_db_connection():
    """设备管理模块用"""
    return get_direct_connection(**CONTAINER_MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT)
