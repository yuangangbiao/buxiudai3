# -*- coding: utf-8 -*-
"""
models/order.py OrderDAO 单元测试（已验证 API）
"""
import pytest
from unittest.mock import patch, MagicMock


class TestOrderDAOQueries:
    """OrderDAO 查询操作 - 基于实际 API 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        for m in list(sys.modules.keys()):
            if m.startswith('models.order'):
                del sys.modules[m]
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

    def _patch(self):
        p = patch('models.database.get_connection', return_value=self.mock_conn)
        p.start()
        return p

    def test_get_by_id_found(self):
        self.mock_cursor.fetchone.return_value = {"id": 1, "order_no": "TEST001"}
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_by_id(1)
        assert result["id"] == 1
        p.stop()

    def test_get_by_id_not_found(self):
        self.mock_cursor.fetchone.return_value = None
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_by_id(999)
        assert result is None
        p.stop()

    def test_get_all_no_filters(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_all()
        assert len(result) == 2
        p.stop()

    def test_get_all_with_filters(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_all(filters={"status": "进行中"})
        assert len(result) == 1
        p.stop()

    def test_get_by_status(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_by_status("进行中")
        assert len(result) == 2
        p.stop()

    def test_fuzzy_search(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1, "order_no": "ABC"}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().fuzzy_search("ABC")
        assert len(result) == 1
        p.stop()

    def test_get_unscheduled(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_unscheduled()
        assert isinstance(result, list)
        p.stop()

    def test_get_province_data(self):
        self.mock_cursor.fetchall.return_value = [{"province": "广东", "count": 50}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_province_data()
        assert len(result) == 1
        assert result[0]["province"] == "广东"
        p.stop()

    def test_batch_get_empty(self):
        """空列表返回空字典"""
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().batch_get_order_statistics([])
        assert result == {}
        p.stop()

    def test_get_process_records(self):
        self.mock_cursor.fetchall.return_value = [{"process_name": "编织", "status": "进行中"}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_process_records(1)
        assert isinstance(result, list)
        p.stop()

    def test_get_quality_records(self):
        self.mock_cursor.fetchall.return_value = [{"check_result": "合格", "quantity": 100}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_quality_records(1)
        assert isinstance(result, list)
        p.stop()

    def test_get_shipments(self):
        self.mock_cursor.fetchall.return_value = [{"shipment_no": "SHP001", "status": "已发货"}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_shipments(1)
        assert isinstance(result, list)
        p.stop()

    def test_get_status_logs(self):
        self.mock_cursor.fetchall.return_value = [{"status": "已下单", "operator": "张三"}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_status_logs(1)
        assert isinstance(result, list)
        p.stop()

    def test_get_production_order(self):
        self.mock_cursor.fetchone.return_value = {"order_id": 1, "production_plan": "计划A"}
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_production_order(1)
        assert result["order_id"] == 1
        p.stop()

    def test_get_dashboard_order_list(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_dashboard_order_list(limit=20)
        assert isinstance(result, list)
        p.stop()

    def test_get_recent_for_list(self):
        self.mock_cursor.fetchall.return_value = [{"id": i} for i in range(10)]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_recent_for_list(limit=50)
        assert len(result) == 10
        p.stop()

    def test_get_recent_for_kanban(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1, "status": "待开始"}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_recent_for_kanban(limit=200)
        assert isinstance(result, list)
        p.stop()

    def test_get_delivery_alert_orders(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_delivery_alert_orders(days_ahead=7)
        assert isinstance(result, list)
        p.stop()

    def test_get_archived_orders(self):
        self.mock_cursor.fetchall.return_value = [{"id": 1, "archived": True}]
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_archived_orders(filters={"year": 2025})
        assert isinstance(result, list)
        p.stop()

    def test_delete_order_found(self):
        self.mock_cursor.rowcount = 1
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().delete(1)
        assert result is True
        p.stop()


class TestOrderDAOPagination:
    """OrderDAO 分页测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        import sys
        for m in list(sys.modules.keys()):
            if m.startswith('models.order'):
                del sys.modules[m]
        self.mock_cursor = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

    def _patch(self):
        p = patch('models.database.get_connection', return_value=self.mock_conn)
        p.start()
        return p

    def test_get_all_paginated(self):
        """分页返回 'data' 而非 'items'"""
        self.mock_cursor.fetchall.return_value = [{"id": 1}]
        self.mock_cursor.fetchone.return_value = {"total": 100}
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_all_paginated(page=1, page_size=20)
        assert "data" in result
        assert "total" in result
        assert "page" in result
        p.stop()

    def test_get_all_paginated_page_2(self):
        self.mock_cursor.fetchall.return_value = [{"id": 21}]
        self.mock_cursor.fetchone.return_value = {"total": 100}
        p = self._patch()
        from models.order import OrderDAO
        result = OrderDAO().get_all_paginated(page=2, page_size=20)
        assert result["page"] == 2
        p.stop()

