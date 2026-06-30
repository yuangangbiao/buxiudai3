# -*- coding: utf-8 -*-
"""
services/inventory_sync.py 测试 - InventorySyncService
"""
import pytest
from unittest.mock import patch, MagicMock


class TestInventorySyncServiceInit:
    """初始化测试"""

    def test_init(self):
        from services.inventory_sync import InventorySyncService
        svc = InventorySyncService()
        assert svc.dao is not None


class TestInventorySyncServiceGetUnifiedStock:
    """get_unified_stock 测试"""

    @patch('services.inventory_sync.InventoryDAO')
    def test_get_unified_stock(self, mock_dao_cls):
        mock_dao = MagicMock()
        mock_dao.get_all.return_value = [{"material_name": "不锈钢丝", "qty": 100}]
        mock_dao_cls.return_value = mock_dao

        from services.inventory_sync import InventorySyncService
        svc = InventorySyncService()
        result = svc.get_unified_stock("不锈钢")
        # 返回的是 list 或其他类型
        assert result is not None


class TestInventorySyncServiceCheckDuplicate:
    """check_duplicate_databases 测试"""

    @patch('services.inventory_sync.get_connection')
    def test_check_duplicate_databases(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_conn.return_value.close.return_value = None

        from services.inventory_sync import InventorySyncService
        svc = InventorySyncService()
        result = svc.check_duplicate_databases()
        assert isinstance(result, bool)

    @patch('core.db.get_direct_connection')
    def test_check_duplicate_databases_found_tables(self, mock_connect):
        """检测到独立 inventory_db 且有表 -> return True"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("inventory",), ("materials",)]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from services.inventory_sync import InventorySyncService
        svc = InventorySyncService()
        result = svc.check_duplicate_databases()
        assert result is True
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SHOW TABLES")
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('core.db.get_direct_connection')
    def test_check_duplicate_databases_connect_fails(self, mock_connect):
        """连接 inventory_db 失败 (pymysql 2003) -> 白名单回落 -> return False"""
        import pymysql
        mock_connect.side_effect = pymysql.err.OperationalError(2003, "Connection refused")

        from services.inventory_sync import InventorySyncService
        svc = InventorySyncService()
        result = svc.check_duplicate_databases()
        assert result is False
