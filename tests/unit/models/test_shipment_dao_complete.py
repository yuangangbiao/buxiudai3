# -*- coding: utf-8 -*-
"""
models/shipment.py ShipmentDAO 单元测试（已验证 API）
"""
import pytest
from unittest.mock import patch, MagicMock


class TestShipmentDAO:
    """ShipmentDAO 测试 - 基于实际 API"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        for m in list(sys.modules.keys()):
            if m.startswith('models.shipment'):
                del sys.modules[m]
            if m.startswith('models.quality'):
                del sys.modules[m]
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=self.mock_cursor)
        self.mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

    def _patch(self):
        p = patch('models.shipment.get_connection', return_value=self.mock_conn)
        p.start()
        return p

    def test_create_shipment(self):
        self.mock_cursor.lastrowid = 100
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().create({"order_id": 1, "shipment_no": "SHP001", "quantity": 50})
        assert result == 100
        p.stop()

    def test_get_by_id_found(self):
        self.mock_cursor.fetchone.return_value = {"id": 1, "shipment_no": "SHP001"}
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_by_id(1)
        assert result["id"] == 1
        p.stop()

    def test_get_by_id_not_found(self):
        self.mock_cursor.fetchone.return_value = None
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_by_id(999)
        assert result is None
        p.stop()

    def test_get_by_shipment_no(self):
        self.mock_cursor.fetchone.return_value = {"id": 5, "shipment_no": "ABC123"}
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_by_shipment_no("ABC123")
        assert result["shipment_no"] == "ABC123"
        p.stop()

    def test_get_all_no_filter(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_all()
        assert len(result) == 2
        p.stop()

    def test_get_all_with_limit(self):
        self.mock_cursor.fetchall.return_value = [{"id": i} for i in range(5)]
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_all(limit=5)
        assert len(result) == 5
        p.stop()

    def test_get_all_shipments(self):
        self.mock_cursor.fetchall.return_value = []
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_all_shipments(filters={"status": "已发货"})
        assert isinstance(result, list)
        p.stop()

    def test_get_recent_for_dashboard(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_recent_for_dashboard(limit=10)
        assert isinstance(result, list)
        p.stop()

    def test_get_finished_goods(self):
        self.mock_cursor.fetchall.return_value = [{"fg_id": 1}]
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_finished_goods(order_id=10, days_limit=30)
        assert isinstance(result, list)
        p.stop()

    def test_get_finished_goods_by_id(self):
        self.mock_cursor.fetchone.return_value = {"fg_id": 5, "quantity": 100}
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_finished_goods_by_id(5)
        assert result["fg_id"] == 5
        p.stop()

    def test_save_tracking(self):
        self.mock_cursor.rowcount = 1
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().save_tracking(1, "SF123", "3", "派送中", [], "SF")
        assert result is True
        p.stop()

    def test_get_tracking_history(self):
        self.mock_cursor.fetchall.return_value = [{"state": "1"}, {"state": "2"}]
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_tracking_history(1, limit=5)
        assert len(result) == 2
        p.stop()

    def test_get_all_with_latest_tracking(self):
        self.mock_cursor.fetchall.return_value = []
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_all_with_latest_tracking()
        assert isinstance(result, list)
        p.stop()

    def test_save_tracking_empty_traces(self):
        self.mock_cursor.rowcount = 1
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().save_tracking(1, "SF123", "3", "派送中", [], "SF")
        assert result is True
        p.stop()

    def test_get_tracking_history_no_limit(self):
        self.mock_cursor.fetchall.return_value = [{"state": "1"}]
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_tracking_history(1)
        assert isinstance(result, list)
        p.stop()

    def test_get_recent_for_dashboard_default_limit(self):
        self.mock_cursor.fetchall.return_value = []
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_recent_for_dashboard()
        assert isinstance(result, list)
        p.stop()

    def test_get_all_with_latest_tracking_with_filters(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        p = self._patch()
        from models.shipment import ShipmentDAO
        result = ShipmentDAO().get_all_with_latest_tracking(filters={"status": "已发货"})
        assert isinstance(result, list)
        p.stop()
