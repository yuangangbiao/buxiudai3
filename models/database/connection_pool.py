# -*- coding: utf-8 -*-
"""
向后兼容桥接层

归档说明:
    v3.0 重构将 connection_pool.py 归档至 _archive/legacy_db/。
    替代实现: core.db.MySQLConnectionPool / get_connection()。

本文件仅做向后兼容:
    1. 旧测试 patch `models.database.connection_pool.get_connection`
       依赖本文件存在
    2. 新代码应直接 import: from models.database import get_connection
"""
from core.db import get_connection

__all__ = ['get_connection']
