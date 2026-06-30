# -*- coding: utf-8 -*-
"""
models/shipment.py 完整单元测试

覆盖模块:
- ShipmentDAO
"""
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestShipmentDAOExists:
    """ShipmentDAO 存在性测试"""

    def test_shipment_dao_class_exists(self):
        """测试ShipmentDAO类存在"""
        from models.shipment import ShipmentDAO
        assert ShipmentDAO is not None

    def test_shipment_dao_has_create_method(self):
        """测试create方法存在"""
        from models.shipment import ShipmentDAO
        assert hasattr(ShipmentDAO, 'create')
        assert callable(ShipmentDAO.create)

    def test_shipment_dao_has_confirm_ship_method(self):
        """测试confirm_ship方法存在"""
        from models.shipment import ShipmentDAO
        assert hasattr(ShipmentDAO, 'confirm_ship')

    def test_shipment_dao_has_get_by_id_method(self):
        """测试get_by_id方法存在"""
        from models.shipment import ShipmentDAO
        assert hasattr(ShipmentDAO, 'get_by_id')


class TestShipmentStatusConstants:
    """ShipmentStatus 状态常量测试"""

    def test_shipment_status_pending_exists(self):
        """测试待发货状态存在"""
        from constants import ShipmentStatus
        assert hasattr(ShipmentStatus, 'PENDING')

    def test_shipment_status_completed_exists(self):
        """测试已发货状态存在"""
        from constants import ShipmentStatus
        assert hasattr(ShipmentStatus, 'COMPLETED')


class TestShipmentDAOGetById:
    """ShipmentDAO.get_by_id 测试"""

    @patch('models.shipment.get_connection')
    def test_get_by_id_success(self, mock_get_conn):
        """测试根据ID获取发货记录成功"""
        from models.shipment import ShipmentDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'id': 1,
            'shipment_no': 'SHIP001',
            'status': '待发货',
            'order_id': 10
        }

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = ShipmentDAO.get_by_id(1)

        assert result is not None
        assert result['id'] == 1

    @patch('models.shipment.get_connection')
    def test_get_by_id_not_found(self, mock_get_conn):
        """测试发货记录不存在"""
        from models.shipment import ShipmentDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = ShipmentDAO.get_by_id(999)

        assert result is None


class TestShipmentDAOGetAll:
    """ShipmentDAO.get_all 测试"""

    @patch('models.shipment.get_connection')
    def test_get_all_returns_list(self, mock_get_conn):
        """测试获取所有发货记录"""
        from models.shipment import ShipmentDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'shipment_no': 'SHIP001', 'status': '待发货'},
            {'id': 2, 'shipment_no': 'SHIP002', 'status': '已发货'},
            {'id': 3, 'shipment_no': 'SHIP003', 'status': '待发货'}
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = ShipmentDAO.get_all()

        assert isinstance(result, list)
        assert len(result) == 3

    @patch('models.shipment.get_connection')
    def test_get_all_empty(self, mock_get_conn):
        """测试没有发货记录"""
        from models.shipment import ShipmentDAO

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_get_conn.return_value = mock_conn

        result = ShipmentDAO.get_all()

        assert isinstance(result, list)
        assert len(result) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
