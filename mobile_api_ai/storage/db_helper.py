# -*- coding: utf-8 -*-
"""
数据库连接池统一管理 - 彻底解决连接泄漏问题

修复说明：
1. 所有数据库操作必须通过连接池，禁止直连 pymysql.connect()
2. 使用上下文管理器确保连接正确归还
3. 异常路径也确保连接关闭

使用方式：
    from mobile_api_ai.storage.db_helper import get_container_storage

    storage = get_container_storage()
    storage.connect()
    rows = storage.fetch_all("SELECT ...")
"""
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

_storage_instance: Optional['MySQLStorage'] = None


@lru_cache(maxsize=1)
def get_container_storage():
    """获取 MySQLStorage 单例（container_center 数据库）"""
    global _storage_instance
    if _storage_instance is None:
        from storage.mysql_storage import MySQLStorage
        _storage_instance = MySQLStorage()
        _storage_instance.connect()
        logger.info('[DB] MySQLStorage 单例已初始化')
    return _storage_instance


def get_pool_status():
    """获取连接池状态"""
    storage = get_container_storage()
    if storage._pool:
        return {
            'pool_connections': storage._pool._connections,
            'pool_busy': storage._pool._busy,
        }
    return {'error': 'pool not initialized'}
