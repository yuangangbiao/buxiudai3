# -*- coding: utf-8 -*-
"""
Supplementary tests for services/inventory_notifier.py
Covers lines/gaps NOT tested in test_inventory_notifier_complete.py
"""
import time
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset singleton and global state before each test."""
    import services.inventory_notifier as mod
    mod.InventoryNotifier._instance = None
    mod._http_factory = None
    # Reset module-level cache for get_inventory_notifier
    mod._inventory_notifier = None


# ============================================================================
# Gap 1: set_http_factory() + _do_http_request() factory branch  (lines 20-31)
# ============================================================================

class TestHttpFactory:
    """Cover set_http_factory and _do_http_request factory vs fallback."""

    def test_set_http_factory_sets_global(self):
        """set_http_factory should set the global _http_factory."""
        from services.inventory_notifier import set_http_factory, _do_http_request
        import services.inventory_notifier as mod

        factory = MagicMock(return_value="factory_result")
        set_http_factory(factory)
        assert mod._http_factory is factory

    def test_do_http_request_uses_factory_when_set(self):
        """_do_http_request should delegate to factory when set."""
        from services.inventory_notifier import set_http_factory, _do_http_request

        mock_factory = MagicMock(return_value="mocked_result")
        set_http_factory(mock_factory)

        req = MagicMock()
        result = _do_http_request(req, timeout=5)
        assert result == "mocked_result"
        mock_factory.assert_called_once_with(req, 5)

    @patch('urllib.request.urlopen')
    def test_do_http_request_fallback_urlopen(self, mock_urlopen):
        """_do_http_request should fall back to urlopen when no factory set."""
        from services.inventory_notifier import _do_http_request

        mock_response = MagicMock()
        mock_urlopen.return_value = mock_response

        req = MagicMock()
        result = _do_http_request(req, timeout=10)
        assert result is mock_response
        mock_urlopen.assert_called_once_with(req, timeout=10)


# ============================================================================
# Gap 2: Circuit breaker import paths  (lines 33-38)
# ============================================================================

class TestCircuitBreaker:
    """Cover circuit breaker import handling."""

    def test_circuit_breaker_imported_when_available(self):
        """When the import succeeds, _cb should be a CircuitBreaker instance."""
        from services.inventory_notifier import _cb
        # Normal import path (the module IS importable in this project)
        assert _cb is not None

    @patch('services.inventory_notifier._do_http_request')
    def test_notifier_graceful_without_circuit_breaker(self, mock_http):
        """Simulate circuit breaker not available: notifier should work without it."""
        import services.inventory_notifier as mod
        # Simulate missing circuit breaker
        mod._cb = None

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_http.return_value = mock_response

        from services.inventory_notifier import InventoryNotifier

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {"host": "localhost", "port": 8080, "enabled": True,
                            "timeout": 5, "api_key": "test"}

        result = notifier.notify_material_prepared("ORD-001", "客户", [{"name": "丝"}])
        assert result["status"] == "ok"


# ============================================================================
# Gap 3: __new__() singleton with double-check locking  (lines 49-56)
# ============================================================================

class TestSingleton:
    """Cover InventoryNotifier singleton __new__ behavior."""

    def test_singleton_returns_same_instance(self):
        """Two calls to InventoryNotifier() should return the same object."""
        from services.inventory_notifier import InventoryNotifier

        a = InventoryNotifier()
        b = InventoryNotifier()
        assert a is b

    def test_singleton_initial_enabled_false(self):
        """Fresh singleton should have _enabled=False (default in __new__)."""
        from services.inventory_notifier import InventoryNotifier

        instance = InventoryNotifier()
        # __new__ sets _enabled=False by default
        assert instance._enabled is False
        assert instance._config is None


# ============================================================================
# Gap 4: init() with default config  (lines 58-64)
# ============================================================================

class TestInitMethod:
    """Cover init() method with default and custom config."""

    @patch('services.inventory_notifier.INVENTORY_SYSTEM_CONFIG',
           {"enabled": True, "host": "default-host", "port": 9999})
    def test_init_with_none_uses_default_config(self, *_):
        """init(None) should use INVENTORY_SYSTEM_CONFIG defaults."""
        from services.inventory_notifier import InventoryNotifier

        notifier = InventoryNotifier()  # goes through __new__ -> _enabled=False

        assert notifier._enabled is False  # default from __new__ before init

        notifier.init(config=None)  # uses INVENTORY_SYSTEM_CONFIG (patched)

        assert notifier._enabled is True
        assert notifier._config["host"] == "default-host"

    def test_init_with_custom_config(self):
        """init() with custom dict should use provided values."""
        from services.inventory_notifier import InventoryNotifier

        notifier = InventoryNotifier()
        config = {"enabled": False, "host": "my-host", "port": 1234}
        notifier.init(config=config)

        assert notifier._enabled is False
        assert notifier._config["host"] == "my-host"
        assert notifier._config["port"] == 1234


# ============================================================================
# Gap 5: _make_request() generic Exception branch  (lines 105-110)
# ============================================================================

class TestMakeRequestGenericException:
    """Cover the generic Exception handler in _make_request."""

    @patch('services.inventory_notifier._do_http_request')
    def test_generic_exception_handler(self, mock_http):
        """When _do_http_request raises a generic Exception, handler should catch it."""
        from services.inventory_notifier import InventoryNotifier

        mock_http.side_effect = RuntimeError("unexpected error")

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {
            "host": "localhost", "port": 8080,
            "enabled": True, "timeout": 5, "api_key": "test"
        }

        result = notifier._make_request("/test", method="GET")
        assert result == {"error": "unknown", "message": "unexpected error"}


# ============================================================================
# Gap 6: notify_order_started() enabled mode  (lines 142-166)
# ============================================================================

class TestNotifyOrderStartedEnabled:
    """Cover notify_order_started when enabled."""

    def test_notify_order_started_sends_correct_payload(self):
        """notify_order_started should construct correct payload and return result."""
        from services.inventory_notifier import InventoryNotifier

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {
            "host": "localhost", "port": 8080,
            "enabled": True, "timeout": 5, "api_key": "test"
        }

        with patch.object(notifier, '_make_request',
                          return_value={"status": "confirmed", "code": 200}) as mock_make_request:

            materials = [{"name": "不锈钢网带", "spec": "304", "qty": 100, "unit": "米"}]
            result = notifier.notify_order_started(
                "ORD-001", "客户A", materials, "2026-06-15"
            )

            assert result == {"status": "confirmed", "code": 200}
            mock_make_request.assert_called_once()

    def test_notify_order_started_payload_structure(self):
        """Verify the payload structure sent to _make_request."""
        from services.inventory_notifier import InventoryNotifier

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {
            "host": "localhost", "port": 8080,
            "enabled": True, "timeout": 5, "api_key": "test"
        }

        materials = [{"name": "网带", "qty": 50}]

        with patch.object(notifier, '_make_request',
                          return_value={"status": "confirmed"}) as mock_make_request:
            notifier.notify_order_started("ORD-002", "客户B", materials, "2026-07-01")

        mock_make_request.assert_called_once()
        call_args = mock_make_request.call_args[0]
        call_kwargs = mock_make_request.call_args[1]

        endpoint = call_kwargs.get("endpoint", call_args[0] if len(call_args) > 0 else "")
        method = call_kwargs.get("method", call_args[1] if len(call_args) > 1 else "GET")
        payload = call_kwargs.get("data", call_args[2] if len(call_args) > 2 else None)

        assert endpoint == "/api/material-demand"
        assert method == "POST"
        assert payload["source_system"] == "steel_belt_tracking"
        assert payload["event_type"] == "order_started"
        assert payload["order_no"] == "ORD-002"
        assert payload["customer_name"] == "客户B"
        assert payload["materials"] == materials
        assert payload["delivery_date"] == "2026-07-01"


# ============================================================================
# Gap 7: wait_for_response() enabled mode  (lines 175-209)
# ============================================================================

class TestWaitForResponseEnabled:
    """Cover wait_for_response polling behavior."""

    def test_wait_for_response_immediate_result(self):
        """If result is not pending, return immediately without sleeping."""
        from services.inventory_notifier import InventoryNotifier

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {
            "host": "localhost", "port": 8080, "enabled": True,
            "timeout": 5, "api_key": "test"
        }

        with patch.object(notifier, '_make_request',
                          return_value={"status": "confirmed", "data": "ok"}) as mock_req:
            with patch('services.inventory_notifier.time.sleep') as mock_sleep:
                result = notifier.wait_for_response("NID-001", timeout=30, poll_interval=2)

                assert result == {"status": "confirmed", "data": "ok"}
                mock_req.assert_called_once_with("/api/response/NID-001", method="GET")
                mock_sleep.assert_not_called()

    def test_wait_for_response_pending_then_success(self):
        """If result is pending once, then success on retry."""
        from services.inventory_notifier import InventoryNotifier

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {
            "host": "localhost", "port": 8080, "enabled": True,
            "timeout": 30, "api_key": "test"
        }

        call_count = [0]
        results = [
            {"status": "pending"},
            {"status": "confirmed", "data": "done"}
        ]

        def mock_request(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return results[idx]

        with patch.object(notifier, '_make_request', side_effect=mock_request):
            with patch('services.inventory_notifier.time.sleep') as mock_sleep:
                with patch('services.inventory_notifier.time.time', return_value=100.0):
                    result = notifier.wait_for_response("NID-002", timeout=30, poll_interval=2)

                    assert result == {"status": "confirmed", "data": "done"}
                    # Should have called _make_request exactly 2 times
                    # sleep is called after the pending response
                    mock_sleep.assert_called_once_with(2)

    def test_wait_for_response_timeout(self):
        """If response stays pending until timeout, return timeout status."""
        from services.inventory_notifier import InventoryNotifier

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {
            "host": "localhost", "port": 8080, "enabled": True,
            "timeout": 10, "api_key": "test"
        }

        # Simulate time progression each time time.time is called
        time_values = [100.0, 100.0, 105.0, 105.0, 112.0, 112.0]
        time_idx = [0]

        def mock_time():
            idx = time_idx[0]
            if idx < len(time_values):
                v = time_values[idx]
            else:
                v = time_values[-1]
            time_idx[0] += 1
            return v

        with patch.object(notifier, '_make_request',
                          return_value={"status": "pending"}) as mock_req:
            with patch('services.inventory_notifier.time.sleep') as mock_sleep:
                with patch('services.inventory_notifier.time.time', side_effect=mock_time):
                    result = notifier.wait_for_response("NID-003", timeout=5, poll_interval=2)

                    assert result == {"status": "timeout", "message": "等待响应超时"}
                    # sleep should have been called for each poll interval
                    assert mock_sleep.call_count >= 1


# ============================================================================
# Gap 8: Module-level shortcut functions  (lines 235-255)
# ============================================================================

class TestModuleLevelFunctions:
    """Cover get_inventory_notifier, notify_material_prepared, notify_order_started."""

    def test_get_inventory_notifier_returns_instance(self):
        """get_inventory_notifier should return an InventoryNotifier instance."""
        from services.inventory_notifier import get_inventory_notifier, InventoryNotifier

        instance = get_inventory_notifier()
        assert isinstance(instance, InventoryNotifier)

    def test_get_inventory_notifier_is_singleton(self):
        """get_inventory_notifier should return the same instance on repeated calls."""
        from services.inventory_notifier import get_inventory_notifier

        a = get_inventory_notifier()
        b = get_inventory_notifier()
        assert a is b

    @patch('services.inventory_notifier.get_inventory_notifier')
    def test_notify_material_prepared_delegates(self, mock_get):
        """notify_material_prepared should delegate to instance method."""
        from services.inventory_notifier import notify_material_prepared

        mock_notifier = MagicMock()
        mock_notifier.notify_material_prepared.return_value = {"status": "confirmed"}
        mock_get.return_value = mock_notifier

        result = notify_material_prepared("ORD-001", "客户", [{"name": "丝"}], deadline="2026-06-01")

        assert result == {"status": "confirmed"}
        mock_notifier.notify_material_prepared.assert_called_once_with(
            "ORD-001", "客户", [{"name": "丝"}], "2026-06-01"
        )

    @patch('services.inventory_notifier.get_inventory_notifier')
    def test_notify_order_started_delegates(self, mock_get):
        """notify_order_started should delegate to instance method."""
        from services.inventory_notifier import notify_order_started

        mock_notifier = MagicMock()
        mock_notifier.notify_order_started.return_value = {"status": "confirmed"}
        mock_get.return_value = mock_notifier

        result = notify_order_started("ORD-001", "客户", [{"name": "丝"}], "2026-06-01")

        assert result == {"status": "confirmed"}
        mock_notifier.notify_order_started.assert_called_once_with(
            "ORD-001", "客户", [{"name": "丝"}], "2026-06-01"
        )


# ============================================================================
# Additional Gap: check_connection() result=None branch  (line 173)
# ============================================================================

class TestCheckConnectionNoneBranch:
    """Cover check_connection when _make_request returns None/falsy."""

    def test_check_connection_returns_false_when_result_is_none(self):
        """When _make_request returns None, check_connection should return (False, '连接失败')."""
        from services.inventory_notifier import InventoryNotifier

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {
            "host": "localhost", "port": 8080,
            "enabled": True, "timeout": 5, "api_key": "test"
        }

        with patch.object(notifier, '_make_request', return_value=None):
            ok, msg = notifier.check_connection()
            assert ok is False
            assert msg == "连接失败"

    def test_check_connection_returns_false_when_result_has_error(self):
        """When _make_request returns a dict with 'error', check_connection should return (False, message)."""
        from services.inventory_notifier import InventoryNotifier

        notifier = InventoryNotifier.__new__(InventoryNotifier)
        notifier._enabled = True
        notifier._config = {
            "host": "localhost", "port": 8080,
            "enabled": True, "timeout": 5, "api_key": "test"
        }

        with patch.object(notifier, '_make_request',
                          return_value={"error": "connection_failed", "message": "超时"}):
            ok, msg = notifier.check_connection()
            assert ok is False
            assert msg == "超时"
