# -*- coding: utf-8 -*-
"""同步模块公共工具 — mysql_cursor / container_cursor"""

from contextlib import contextmanager
from core.db import get_direct_connection
from core.config import MYSQL_CFG, CONTAINER_MYSQL_CFG, DB_CONNECT_TIMEOUT


@contextmanager
def mysql_cursor():
    """steel_belt 读写上下文（自动 commit / rollback）"""
    from db.steelbelt_pool import get_conn
    conn = get_conn()
    conn.autocommit(False)
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def container_cursor():
    """container_center 读写上下文（自动 commit / rollback）"""
    conn = get_direct_connection(**CONTAINER_MYSQL_CFG, autocommit=False,

                           connect_timeout=DB_CONNECT_TIMEOUT)
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
