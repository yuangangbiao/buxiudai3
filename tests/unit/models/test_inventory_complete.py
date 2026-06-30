# -*- coding: utf-8 -*-
"""
models/inventory.py 完整单元测试

覆盖模块:
- InventoryDAO
"""
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestInventoryDAOExists:
    """InventoryDAO 存在性测试"""

    def test_inventory_dao_class_exists(self):
        """测试InventoryDAO类存在"""
        from models.inventory import InventoryDAO
        assert InventoryDAO is not None

    def test_inventory_dao_has_create_method(self):
        """测试create方法存在"""
        from models.inventory import InventoryDAO
        assert hasattr(InventoryDAO, 'create')
        assert callable(InventoryDAO.create)

    def test_inventory_dao_has_update_method(self):
        """测试update方法存在"""
        from models.inventory import InventoryDAO
        assert hasattr(InventoryDAO, 'update')

    def test_inventory_dao_has_stock_in_method(self):
        """测试stock_in方法存在"""
        from models.inventory import InventoryDAO
        assert hasattr(InventoryDAO, 'stock_in')

    def test_inventory_dao_has_get_all_method(self):
        """测试get_all方法存在"""
        from models.inventory import InventoryDAO
        assert hasattr(InventoryDAO, 'get_all')


class TestInventoryDAOGetAll:
    """InventoryDAO.get_all 测试"""

    @patch('models.inventory.get_connection')
    def test_get_all_returns_list(self, mock_get_conn):
        """测试获取所有库存"""
        from models.inventory import InventoryDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'material_name': '不锈钢丝', 'quantity': 100},
            {'id': 2, 'material_name': '铁丝', 'quantity': 200}
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = InventoryDAO.get_all()

        assert isinstance(result, list)
        assert len(result) == 2

    @patch('models.inventory.get_connection')
    def test_get_all_empty(self, mock_get_conn):
        """测试没有库存"""
        from models.inventory import InventoryDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = InventoryDAO.get_all()

        assert isinstance(result, list)
        assert len(result) == 0


class TestInventoryDAOStockIn:
    """InventoryDAO.stock_in 测试"""

    @patch('models.inventory.get_connection')
    def test_stock_in_success(self, mock_get_conn):
        """测试入库成功"""
        from models.inventory import InventoryDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (100,)  # 当前库存

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = InventoryDAO.stock_in(1, 50)

        assert result is True
        mock_conn.commit.assert_called()

    @patch('models.inventory.get_connection')
    def test_stock_in_with_order(self, mock_get_conn):
        """测试带订单入库"""
        from models.inventory import InventoryDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (50,)  # 当前库存

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = InventoryDAO.stock_in(1, 100, order_id=10, operator="张三")

        assert result is True


class TestInventoryDAOStockOut:
    """InventoryDAO.stock_out 测试"""

    @patch('models.inventory.get_connection')
    def test_stock_out_success(self, mock_get_conn):
        """测试出库成功"""
        from models.inventory import InventoryDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (100,)  # 当前库存

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = InventoryDAO.stock_out(1, 30)

        assert result is True
        mock_conn.commit.assert_called()

    @patch('models.inventory.get_connection')
    def test_stock_out_insufficient(self, mock_get_conn):
        """测试库存不足"""
        from models.inventory import InventoryDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (10,)  # 当前库存不足

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = InventoryDAO.stock_out(1, 100)

        assert result is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
