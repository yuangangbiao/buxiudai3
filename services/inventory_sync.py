# -*- coding: utf-8 -*-
"""库存同步服务 - 统一库存查询与去重"""

import os
import pymysql
from core import db
from core.db import get_connection  # 兼容旧 patch
from models.inventory import InventoryDAO

__all__ = ['InventorySyncService']


class InventorySyncService:
    def __init__(self):
        self.dao = InventoryDAO()

    def get_unified_stock(self, material_prefix: str):
        return self.dao.search_by_material(material_prefix)

    def check_duplicate_databases(self) -> bool:
        """检查是否存在独立 inventory_db 库存库（去重检测）。

        业务意义：早期部分环境可能在独立 inventory_db 库存放库存表，
        与 steel_belt.inventory 重复。返回 True 表示检测到独立库（建议去重）；
        返回 False 表示无独立库 / 库连不上 / 库不存在。
        异常处理遵循 F16 教训：仅白名单 MySQL 业务可降级错误（1045 拒绝、1049
        库不存在、2003 连不上）返回 False，其它异常显式上抛，避免静默吞 bug。
        """
        try:
            conn = db.get_direct_connection(
                host=os.getenv('MYSQL_HOST', '127.0.0.1'),
                port=int(os.getenv('MYSQL_PORT', '3306')),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database=os.getenv('INVENTORY_DB_NAME', 'inventory_db'),
                connect_timeout=int(os.getenv('DB_CONNECT_TIMEOUT', '5')),
            )
        except pymysql.err.MySQLError as e:
            # 1045 = Access denied, 1049 = Unknown database, 2003 = Can't connect
            if e.args and e.args[0] in (1045, 1049, 2003):
                return False
            raise
        try:
            cursor = conn.cursor()
            try:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
            finally:
                cursor.close()
            return bool(tables)
        finally:
            conn.close()
