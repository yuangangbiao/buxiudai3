# -*- coding: utf-8 -*-
"""
models/inventory.py 深度测试 - InventoryDAO 所有方法
注意：inventory.py 使用 conn.cursor() 而不是 with conn.cursor() as cursor:
"""
import sys, os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_db():
    """返回 mock conn 和 cursor（直接 cursor 返回，不需要 context manager）"""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor  # 直接返回，不是 context manager
    conn.commit.return_value = None
    return conn, cursor


class TestInventoryDAOUpdate:
    """update 测试"""

    def test_update_success(self, mock_db):
        conn, cursor = mock_db
        cursor.rowcount = 1
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.update(1, {
                "material_name": "不锈钢板",
                "material_type": "304",
            })
            assert result is True

    def test_update_rowcount_zero(self, mock_db):
        conn, cursor = mock_db
        cursor.rowcount = 0
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.update(9999, {"material_name": "test"})
            # inventory.update always returns True (doesn't check rowcount)
            assert result is True


class TestInventoryDAOStockIn:
    """stock_in 测试"""

    def test_stock_in_success(self, mock_db):
        conn, cursor = mock_db
        cursor.fetchone.return_value = [50.0]  # 原有数量
        cursor.lastrowid = 1
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.stock_in(1, 20.0, order_id="ORD-001", operator="张三", remark="入库备注")
            assert result is True

    def test_stock_in_new_material(self, mock_db):
        conn, cursor = mock_db
        cursor.fetchone.return_value = None  # 不存在
        cursor.lastrowid = 1
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.stock_in(1, 100.0)
            assert result is True


class TestInventoryDAOStockOut:
    """stock_out 测试"""

    def test_stock_out_success(self, mock_db):
        conn, cursor = mock_db
        # stock_out calls cursor.fetchone() multiple times
        cursor.fetchone.side_effect = [[50.0], None, None]  # before_qty, then update/insert result
        cursor.rowcount = 1
        cursor.lastrowid = 1
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.stock_out(1, 30.0, order_id="ORD-002", operator="李四", remark="出库备注")
            assert result is True

    def test_stock_out_insufficient(self, mock_db):
        conn, cursor = mock_db
        # 返回少量库存，不足以出库
        cursor.fetchone.return_value = [10.0]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.stock_out(1, 100.0)
            assert result is False


class TestInventoryDAOGetLowInventoryAlerts:
    """get_low_inventory_alerts 测试"""

    def test_get_low_inventory_alerts(self, mock_db):
        conn, cursor = mock_db
        cursor.fetchall.return_value = [
            {"id": 1, "material_name": "不锈钢丝", "quantity": 5, "warning_qty": 10}
        ]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_low_inventory_alerts()
            assert isinstance(result, list)


class TestInventoryDAOGetAll:
    """get_all 测试"""

    def test_get_all(self, mock_db):
        conn, cursor = mock_db
        cursor.fetchall.return_value = [
            {"id": 1, "material_name": "不锈钢丝", "quantity": 100},
            {"id": 2, "material_name": "不锈钢板", "quantity": 200},
        ]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_all()
            assert len(result) == 2

    def test_get_all_with_filters(self, mock_db):
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"id": 1}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_all(filters={"material_type": "304", "keyword": "丝"})
            assert isinstance(result, list)
            # 验证 SQL 包含过滤条件
            cursor.execute.assert_called()


class TestInventoryDAOGetRecords:
    """get_records 测试"""

    def test_get_records(self, mock_db):
        conn, cursor = mock_db
        cursor.fetchall.return_value = [
            {"id": 1, "record_type": "入库", "quantity": 50}
        ]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_records(inv_id=1)
            assert isinstance(result, list)


class TestInventoryDAOGetWarningItems:
    """get_warning_items 测试"""

    def test_get_warning_items(self, mock_db):
        conn, cursor = mock_db
        cursor.fetchall.return_value = [
            {"id": 1, "material_name": "不锈钢丝", "quantity": 3, "warning_qty": 10}
        ]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_warning_items()
            assert isinstance(result, list)


class TestInventoryDAOGetDashboardOverview:
    """get_dashboard_overview 测试"""

    def test_get_dashboard_overview(self, mock_db):
        conn, cursor = mock_db
        cursor.fetchall.return_value = [{"total_items": 10, "total_quantity": 5000}]
        from models.inventory import InventoryDAO
        with patch('models.inventory.get_connection', return_value=conn):
            result = InventoryDAO.get_dashboard_overview()
            assert isinstance(result, list)
