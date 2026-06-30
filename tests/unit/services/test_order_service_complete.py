# -*- coding: utf-8 -*-
"""
services/order_service.py 测试 - 当前58%，提升到80%+
"""
import pytest
from unittest.mock import patch, MagicMock
from core.exceptions import ValidationException, NotFoundException


class TestOrderServiceStatusFlow:
    """订单状态流转测试 - 覆盖 L48-59"""

    def test_status_flow_draft(self):
        from services.order_service import OrderService
        # STATUS_DRAFT = "待确认"
        draft = OrderService.STATUS_DRAFT
        flow = OrderService.STATUS_FLOW[draft]
        # DRAFT -> CONFIRMED("待排产") or CANCELLED("已取消")
        assert "待排产" in flow
        assert "已取消" in flow

    def test_status_flow_completed(self):
        from services.order_service import OrderService
        # completed 是终态
        assert OrderService.STATUS_FLOW[OrderService.STATUS_COMPLETED] == []

    def test_status_flow_cancelled_can_reopen(self):
        from services.order_service import OrderService
        # cancelled 可以回到 draft
        assert OrderService.STATUS_DRAFT in OrderService.STATUS_FLOW[OrderService.STATUS_CANCELLED]

    def test_status_flow_values_are_chinese(self):
        from services.order_service import OrderService
        assert OrderService.STATUS_DRAFT == "待确认"
        assert OrderService.STATUS_CONFIRMED == "待排产"
        assert OrderService.STATUS_PUBLISHED == "已发布"


class TestOrderServiceSingleton:
    """单例模式测试 - 覆盖 L76-83"""

    def test_get_instance_returns_same(self):
        from services.order_service import OrderService
        instance1 = OrderService.get_instance()
        instance2 = OrderService.get_instance()
        assert instance1 is instance2

    def test_instances_are_order_service(self):
        from services.order_service import OrderService
        instance = OrderService.get_instance()
        assert isinstance(instance, OrderService)


class TestOrderServiceCreateOrder:
    """_create_order 测试 - 覆盖 L128-168"""

    @patch('services.order_service.OrderValidator')
    @patch('services.order_service.generate_order_no')
    @patch('services.order_service.get_connection')
    @patch('services.order_service.AuditService')
    @patch('services.order_service.EventBus')
    def test_create_order_success(self, mock_event_bus, mock_audit, mock_conn, mock_gen_no, mock_validator):
        mock_validator.validate_create.return_value = {"order_no": "ORD-123", "product_type": "重型"}
        mock_gen_no.return_value = "ORD-202605001"
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor
        mock_conn.return_value.close.return_value = None

        mock_dao = MagicMock()
        mock_dao.create.return_value = 1

        from services.order_service import OrderService
        svc = OrderService(dao=mock_dao, audit_service=mock_audit, event_bus=mock_event_bus)
        result = svc._create_order({"product_type": "重型"}, operator="admin")

        assert result['id'] == 1
        assert 'order_no' in result
        mock_audit.log.assert_called_once()
        mock_event_bus.publish.assert_called_once()

    @patch('services.order_service.OrderValidator')
    def test_create_order_validation_failure(self, mock_validator):
        from services.order_service import OrderService
        mock_validator.validate_create.side_effect = ValidationException("产品类型不能为空")
        svc = OrderService()
        with pytest.raises(ValidationException):
            svc._create_order({})


class TestOrderServiceUpdateOrder:
    """_update_order 测试 - 覆盖 L170-194"""

    def test_update_order_not_found(self):
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = None

        from services.order_service import OrderService
        svc = OrderService(dao=mock_dao)
        with pytest.raises(NotFoundException):
            svc._update_order(999, {"status": "CONFIRMED"})

    @patch('services.order_service.OrderValidator')
    def test_update_order_success(self, mock_validator):
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = {"id": 1, "order_no": "ORD-001"}
        mock_dao.update.return_value = True

        mock_audit = MagicMock()
        mock_event_bus = MagicMock()

        from services.order_service import OrderService
        svc = OrderService(dao=mock_dao, audit_service=mock_audit, event_bus=mock_event_bus)
        result = svc._update_order(1, {"status": "待排产"}, operator="admin")

        assert result is True
        mock_audit.log.assert_called_once()


class TestOrderServiceChangeStatus:
    """_change_status 测试 - 覆盖 L196-233"""

    def test_change_status_not_found(self):
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = None

        from services.order_service import OrderService
        svc = OrderService(dao=mock_dao)
        with pytest.raises(NotFoundException):
            svc._change_status(999, "待排产")

    @patch('services.order_service.OrderValidator')
    def test_change_status_invalid_flow(self, mock_validator):
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = {"id": 1, "order_no": "ORD-001", "status": "待确认"}

        from services.order_service import OrderService
        svc = OrderService(dao=mock_dao)
        # DRAFT("待确认") can't go directly to SHIPPED("已发货")
        with pytest.raises(ValidationException) as exc_info:
            svc._change_status(1, "已发货")
        assert "流转无效" in str(exc_info.value)

    def test_change_status_success(self):
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = {"id": 1, "order_no": "ORD-001", "status": "待确认"}
        mock_dao.update.return_value = True

        mock_audit = MagicMock()
        mock_event_bus = MagicMock()

        from services.order_service import OrderService
        svc = OrderService(dao=mock_dao, audit_service=mock_audit, event_bus=mock_event_bus)
        result = svc._change_status(1, "待排产", operator="admin")

        assert result is True


class TestOrderServiceDeleteOrder:
    """_delete_order 测试 - 覆盖 L235-254"""

    def test_delete_order_not_found(self):
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = None

        from services.order_service import OrderService
        svc = OrderService(dao=mock_dao)
        with pytest.raises(NotFoundException):
            svc._delete_order(999)

    def test_delete_order_success(self):
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = {"id": 1, "order_no": "ORD-001"}
        mock_dao.delete.return_value = True

        mock_audit = MagicMock()
        mock_event_bus = MagicMock()

        from services.order_service import OrderService
        svc = OrderService(dao=mock_dao, audit_service=mock_audit, event_bus=mock_event_bus)
        result = svc._delete_order(1, operator="admin")

        assert result is True


class TestOrderServiceGetDetail:
    """_get_order_detail 测试 - 覆盖 L256-268"""

    def test_get_detail_with_extra_params_json(self):
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = {
            "id": 1,
            "order_no": "ORD-001",
            "extra_params": '{"key": "value"}'
        }

        from services.order_service import OrderService
        svc = OrderService(dao=mock_dao)
        result = svc._get_order_detail(1)

        assert result["extra_params"] == {"key": "value"}

    def test_get_detail_with_invalid_json(self):
        mock_dao = MagicMock()
        mock_dao.get_by_id.return_value = {
            "id": 1,
            "order_no": "ORD-001",
            "extra_params": "{ invalid"
        }

        from services.order_service import OrderService
        svc = OrderService(dao=mock_dao)
        result = svc._get_order_detail(1)
        # JSON 解析失败保持原字符串
        assert result["extra_params"] == "{ invalid"


class TestOrderServiceSearchOrders:
    """_search_orders 测试 - 覆盖 L274-276"""

    def test_search_orders(self):
        mock_dao = MagicMock()
        mock_dao.fuzzy_search.return_value = [{"id": 1}, {"id": 2}]

        from services.order_service import OrderService
        svc = OrderService(dao=mock_dao)
        result = svc._search_orders("ORD")
        assert len(result) == 2


class TestOrderServiceGetHistory:
    """_get_order_history 测试 - 覆盖 L270-272"""

    def test_get_order_history_method(self):
        mock_audit = MagicMock()
        mock_audit.ENTITY_ORDER = "ORDER"
        mock_audit.get_entity_history.return_value = [
            {"action": "CREATE", "timestamp": "2026-01-01"}
        ]

        from services.order_service import OrderService
        svc = OrderService(audit_service=mock_audit)
        result = svc._get_order_history(1)

        assert len(result) == 1
        mock_audit.get_entity_history.assert_called_once_with("ORDER", "1")


class TestOrderServiceSyncDelivery:
    """_sync_delivery_date_to_dispatch 测试 - 覆盖 L282-326"""

    @patch('services.order_service.BusinessConfig')
    @patch('services.order_service.requests')
    def test_sync_no_mobile_url(self, mock_requests, mock_config):
        mock_config.MOBILE_API_URL = ""

        from services.order_service import OrderService
        svc = OrderService()
        svc._sync_delivery_date_to_dispatch(
            {"order_no": "ORD-001", "delivery_date": "2026-05-01"},
            {"delivery_date": "2026-06-01"}
        )

    @patch('services.order_service.BusinessConfig')
    @patch('services.order_service.requests')
    def test_sync_same_delivery_date(self, mock_requests, mock_config):
        mock_config.MOBILE_API_URL = "http://mobile.example.com"

        from services.order_service import OrderService
        svc = OrderService()
        svc._sync_delivery_date_to_dispatch(
            {"order_no": "ORD-001", "delivery_date": "2026-05-01"},
            {"delivery_date": "2026-05-01"}
        )
        mock_requests.post.assert_not_called()

    @patch('services.order_service.BusinessConfig')
    @patch('services.order_service.requests')
    def test_sync_no_order_no(self, mock_requests, mock_config):
        mock_config.MOBILE_API_URL = "http://mobile.example.com"

        from services.order_service import OrderService
        svc = OrderService()
        # order_no 为空 → 提前 return
        svc._sync_delivery_date_to_dispatch(
            {"order_no": "", "delivery_date": "2026-05-01"},
            {"delivery_date": "2026-06-01"}
        )
        mock_requests.post.assert_not_called()

    @patch('services.order_service.BusinessConfig')
    @patch('services.order_service.logger')
    def test_sync_delivery_date_timeout(self, mock_logger, mock_config):
        mock_config.MOBILE_API_URL = "http://mobile.example.com"
        import requests as req

        from services.order_service import OrderService
        svc = OrderService()
        # mock threading.Thread.start 让其同步执行 target
        original_thread = __import__('threading').Thread
        captured_target = [None]
        class SyncThread(original_thread):
            def start(self):
                captured_target[0] = self._target
                self._target(*self._args, **self._kwargs)
        with patch('services.order_service.threading.Thread', SyncThread):
            with patch('services.order_service.requests.post',
                       side_effect=req.exceptions.Timeout("timeout")):
                svc._sync_delivery_date_to_dispatch(
                    {"order_no": "ORD-001", "delivery_date": "2026-05-01"},
                    {"delivery_date": "2026-06-01"}
                )
        mock_logger.warning.assert_called_once()

    @patch('services.order_service.BusinessConfig')
    @patch('services.order_service.logger')
    def test_sync_delivery_date_connection_error(self, mock_logger, mock_config):
        mock_config.MOBILE_API_URL = "http://mobile.example.com"
        import requests as req

        from services.order_service import OrderService
        svc = OrderService()
        original_thread = __import__('threading').Thread
        class SyncThread(original_thread):
            def start(self):
                self._target(*self._args, **self._kwargs)
        with patch('services.order_service.threading.Thread', SyncThread):
            with patch('services.order_service.requests.post',
                       side_effect=req.exceptions.ConnectionError("连接失败")):
                svc._sync_delivery_date_to_dispatch(
                    {"order_no": "ORD-001", "delivery_date": "2026-05-01"},
                    {"delivery_date": "2026-06-01"}
                )
        mock_logger.error.assert_called_once()

    @patch('services.order_service.BusinessConfig')
    @patch('services.order_service.logger')
    def test_sync_delivery_date_unexpected_error(self, mock_logger, mock_config):
        mock_config.MOBILE_API_URL = "http://mobile.example.com"

        from services.order_service import OrderService
        svc = OrderService()
        original_thread = __import__('threading').Thread
        class SyncThread(original_thread):
            def start(self):
                self._target(*self._args, **self._kwargs)
        with patch('services.order_service.threading.Thread', SyncThread):
            with patch('services.order_service.requests.post',
                       side_effect=Exception("未知错误")):
                svc._sync_delivery_date_to_dispatch(
                    {"order_no": "ORD-001", "delivery_date": "2026-05-01"},
                    {"delivery_date": "2026-06-01"}
                )
        mock_logger.exception.assert_called_once()

    @patch('services.order_service.BusinessConfig')
    @patch('services.order_service.requests')
    def test_sync_connection_error(self, mock_requests, mock_config):
        mock_config.MOBILE_API_URL = "http://mobile.example.com"
        import requests as req
        mock_requests.post.side_effect = req.exceptions.ConnectionError("连接失败")

        from services.order_service import OrderService
        svc = OrderService()
        # 不应抛出异常
        svc._sync_delivery_date_to_dispatch(
            {"order_no": "ORD-001", "delivery_date": "2026-05-01"},
            {"delivery_date": "2026-06-01"}
        )


class TestOrderServiceClassMethods:
    """@classmethod 委托测试 - 覆盖 L89-122"""

    @patch('services.order_service.OrderService._create_order')
    def test_create_order_classmethod(self, mock_create):
        mock_create.return_value = {"id": 1}
        from services.order_service import OrderService
        result = OrderService.create_order({"product_type": "重型"})
        assert result["id"] == 1

    @patch('services.order_service.OrderService._update_order')
    def test_update_order_classmethod(self, mock_update):
        mock_update.return_value = True
        from services.order_service import OrderService
        result = OrderService.update_order(1, {"status": "待排产"})
        assert result is True

    @patch('services.order_service.OrderService._delete_order')
    def test_delete_order_classmethod(self, mock_delete):
        mock_delete.return_value = True
        from services.order_service import OrderService
        result = OrderService.delete_order(1, operator="admin")
        assert result is True
        mock_delete.assert_called_once_with(1, "admin")

    @patch('services.order_service.OrderService._get_order_detail')
    def test_get_order_detail_classmethod(self, mock_detail):
        mock_detail.return_value = {"id": 1, "order_no": "ORD-001"}
        from services.order_service import OrderService
        result = OrderService.get_order_detail(1)
        assert result["id"] == 1
        mock_detail.assert_called_once_with(1)

    @patch('services.order_service.OrderService._get_order_history')
    def test_get_order_history_classmethod(self, mock_history):
        mock_history.return_value = [{"action": "CREATE"}]
        from services.order_service import OrderService
        result = OrderService.get_order_history(1)
        assert len(result) == 1
        mock_history.assert_called_once_with(1)

    @patch('services.order_service.OrderService._search_orders')
    def test_search_orders_classmethod(self, mock_search):
        mock_search.return_value = [{"id": 1}]
        from services.order_service import OrderService
        result = OrderService.search_orders("ORD")
        assert len(result) == 1
        mock_search.assert_called_once_with("ORD")
