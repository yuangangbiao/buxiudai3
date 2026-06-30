# -*- coding: utf-8 -*-
"""
services/inventory_notifier.py 测试 - InventoryNotifier (HTTP库存通知器)
"""
import pytest
from unittest.mock import patch, MagicMock


class TestInventoryNotifierInit:
    """初始化测试"""

    def test_init_disabled(self):
        from services.inventory_notifier import InventoryNotifier
        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = False
        notifier._config = {}
        assert notifier.is_enabled() is False


class TestInventoryNotifierDisabledMode:
    """禁用模式测试 - _enabled=False"""

    def test_notify_material_prepared_disabled(self):
        from services.inventory_notifier import InventoryNotifier
        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = False
        notifier._config = {}

        result = notifier.notify_material_prepared("ORD-001", "客户", [{"name": "丝"}])
        assert result == {"status": "disabled"}

    def test_notify_order_started_disabled(self):
        from services.inventory_notifier import InventoryNotifier
        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = False
        notifier._config = {}

        result = notifier.notify_order_started("ORD-001", "客户", [{"name": "丝"}], "2026-06-01")
        assert result == {"status": "disabled"}

    def test_get_response_disabled(self):
        from services.inventory_notifier import InventoryNotifier
        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = False
        notifier._config = {}

        result = notifier.get_response("MSG-001")
        assert result == {"status": "disabled"}

    def test_wait_for_response_disabled(self):
        from services.inventory_notifier import InventoryNotifier
        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = False
        notifier._config = {}

        result = notifier.wait_for_response("MSG-001", timeout=1)
        assert result == {"status": "disabled"}


class TestInventoryNotifierEnabledMode:
    """启用模式测试"""

    def test_init_enabled(self):
        from services.inventory_notifier import InventoryNotifier
        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {"host": "localhost", "port": 8080, "enabled": True, "timeout": 5}

        assert notifier.is_enabled() is True

    def test_notify_material_prepared_no_config(self):
        from services.inventory_notifier import InventoryNotifier
        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = None  # 无配置

        result = notifier.notify_material_prepared("ORD-001", "客户", [{"name": "丝"}])
        assert result is None  # _make_request 返回 None 当无配置

    @patch('services.inventory_notifier._do_http_request')
    def test_notify_material_prepared_success(self, mock_http):
        from services.inventory_notifier import InventoryNotifier
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"status": "confirmed"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_http.return_value = mock_response

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {"host": "localhost", "port": 8080, "enabled": True, "timeout": 5, "api_key": "test"}

        result = notifier.notify_material_prepared("ORD-001", "客户", [{"name": "丝"}])
        assert result["status"] == "confirmed"

    @patch('services.inventory_notifier._do_http_request')
    def test_notify_material_prepared_http_error(self, mock_http):
        from services.inventory_notifier import InventoryNotifier
        from urllib.error import HTTPError
        mock_http.side_effect = HTTPError("http://x", 500, "Server Error", {}, None)

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {"host": "localhost", "port": 8080, "enabled": True, "timeout": 5, "api_key": "test"}

        result = notifier.notify_material_prepared("ORD-001", "客户", [{"name": "丝"}])
        assert "error" in result


class TestInventoryNotifierCheckConnection:
    """check_connection 测试"""

    @patch('services.inventory_notifier._do_http_request')
    def test_check_connection_success(self, mock_http):
        from services.inventory_notifier import InventoryNotifier
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_http.return_value = mock_response

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {"host": "localhost", "port": 8080, "enabled": True, "timeout": 5, "api_key": "test"}

        ok, msg = notifier.check_connection()
        assert ok is True

    @patch('services.inventory_notifier._do_http_request')
    def test_check_connection_failure(self, mock_http):
        from services.inventory_notifier import InventoryNotifier
        from urllib.error import URLError
        mock_http.side_effect = URLError("连接被拒绝")

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {"host": "localhost", "port": 8080, "enabled": True, "timeout": 5, "api_key": "test"}

        ok, msg = notifier.check_connection()
        assert ok is False


class TestInventoryNotifierGetResponse:
    """get_response 测试"""

    @patch('services.inventory_notifier._do_http_request')
    def test_get_response_success(self, mock_http):
        from services.inventory_notifier import InventoryNotifier
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"status": "confirmed", "inventory_check": []}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_http.return_value = mock_response

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {"host": "localhost", "port": 8080, "enabled": True, "timeout": 5, "api_key": "test"}

        result = notifier.get_response("MSG-001")
        assert result["status"] == "confirmed"
