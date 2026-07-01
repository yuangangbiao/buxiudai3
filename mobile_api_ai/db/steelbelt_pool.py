# -*- coding: utf-8 -*-
"""SteelBelt MySQL 连接池 — 统一 steel_belt 数据库连接"""
import logging
from dbutils.pooled_db import PooledDB
import pymysql
from pymysql.cursors import DictCursor
from core.config import MYSQL_CFG, DB_CONNECT_TIMEOUT

logger = logging.getLogger(__name__)

_pool = None


def get_conn():
    """获取 steel_belt 连接"""
    global _pool
    if _pool is None:
        _pool = PooledDB(
            creator=pymysql,
            maxconnections=10, mincached=2, maxcached=5,
            blocking=True, ping=1, cursorclass=DictCursor,
            **MYSQL_CFG, connect_timeout=DB_CONNECT_TIMEOUT, autocommit=True,
        )
        logger.info('[SteelBeltPool] 连接池已创建')
    return _pool.connection()


def cursor():
    """快捷获取连接 + DictCursor"""
    conn = get_conn()
    return conn, conn.cursor()
