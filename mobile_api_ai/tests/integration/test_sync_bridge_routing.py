# -*- coding: utf-8 -*-
"""
集成测试: Sync Bridge 数据库连接路由

验证 sync_bridge.py 的 _get_mysql_connection()
连接的是 steel_belt 而非 container_center。
"""
import os
import sys

import pytest


class TestSyncBridgeRouting:
    """sync_bridge 连接路由验证"""

    def test_get_mysql_connection_steel_belt(self):
        """_get_mysql_connection() 连接 steel_belt"""
        from sync_bridge import _get_mysql_connection
        conn = _get_mysql_connection()
        try:
            db_name = conn.db.decode() if isinstance(conn.db, bytes) else str(conn.db)
            assert db_name == 'steel_belt', (
                f'连错库: {db_name}, 期望 steel_belt。'
                f'检查 sync_bridge.py::_get_mysql_connection() '
                f'是否用了 MYSQL_CFG'
            )
        finally:
            conn.close()

    def test_get_mysql_connection_writable(self):
        """_get_mysql_connection() 可执行写操作（验证连接有效）"""
        from sync_bridge import _get_mysql_connection
        conn = _get_mysql_connection()
        try:
            with conn.cursor() as c:
                c.execute("SELECT 1 AS n")
                row = c.fetchone()
                assert row['n'] == 1
        finally:
            conn.close()

    def test_production_orders_exists_in_steel_belt(self):
        """steel_belt.production_orders 表存在（sync_bridge 写入目标）"""
        from sync_bridge import _get_mysql_connection
        conn = _get_mysql_connection()
        try:
            with conn.cursor() as c:
                c.execute("SHOW TABLES LIKE 'production_orders'")
                assert c.fetchone() is not None, (
                    'steel_belt.production_orders 不存在，'
                    '_sync_to_mysql() 无法写入'
                )
        finally:
            conn.close()
