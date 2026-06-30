# -*- coding: utf-8 -*-
"""精准补漏 - error_handler + event_bus + saga 最后缺口"""
import sys, os
import pytest
from unittest.mock import patch, MagicMock


class TestErrorHandlerPush:
    def test_handle_error_with_recognized_code(self):
        from core.error_handler import handle_error
        try:
            raise RuntimeError("Can't connect to MySQL on localhost")
        except RuntimeError as e:
            code, hint = handle_error(type(e), e, e.__traceback__)
            assert code == "ERR-DB-001"

    def test_handle_error_unknown(self):
        from core.error_handler import handle_error
        try:
            raise RuntimeError("totally unrecognizable message xyz123")
        except RuntimeError as e:
            code, hint = handle_error(type(e), e, e.__traceback__)
            assert code is None or code == "UNKNOWN"

    def test_log_error_to_db_fails_gracefully(self):
        from core.error_handler import log_error_to_db
        log_error_to_db("ERR-TEST", "test message")  # should not crash

    def test_recognize_business_error(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("Business rule validation failed for order") == "ERR-BIZ-002"

    def test_recognize_state_error(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("Order status 'pending' does not allow this") == "ERR-BIZ-003"

    def test_recognize_connection_timeout(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("Timeout: Connection timeout after 30s") == "ERR-NET-002"

    def test_recognize_unknown_column(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("Unknown column 'price'") == "ERR-DB-006"

    def test_recognize_unknown_database(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("Unknown database 'test_db'") == "ERR-DB-003"

    def test_recognize_cursor_closed(self):
        from core.error_handler import recognize_error_code
        assert recognize_error_code("cursor is closed") == "ERR-RES-001"


class TestEventBusPush:
    def test_events_class_constants(self):
        from core.event_bus import Events
        assert hasattr(Events, 'ORDER_CREATED')
        assert isinstance(Events.ORDER_CREATED, str)

    def test_on_event_decorator(self):
        from core.event_bus import on_event, EventBus
        received = []
        @on_event('deco:test')
        def handler(ev, d):
            received.append(d)
        EventBus.publish('deco:test', {'x': 1})
        assert len(received) == 1

    def test_module_level_publish(self):
        from core.event_bus import publish, EventBus
        results = {}
        EventBus.subscribe('mod:pub', lambda ev, d: results.update({ev: d}))
        publish('mod:pub', {'val': 42})
        assert results.get('mod:pub', {}).get('val') == 42

    def test_event_bus_factory_create(self):
        from core.event_bus_factory import create_event_bus
        bus = create_event_bus()
        assert bus is not None


class TestSagaPush:
    def test_saga_orchestrator_init(self):
        from core.saga import SagaOrchestrator, SagaStep
        step1 = SagaStep("step1", lambda ctx: True, lambda ctx: None)
        orch = SagaOrchestrator("test-orch", [step1])
        assert orch is not None

    def test_saga_step(self):
        from core.saga import SagaStep
        step = SagaStep("test_step", lambda ctx: True, lambda ctx: None)
        assert step.name == "test_step"

    def test_saga_step_str(self):
        from core.saga import SagaStep
        step = SagaStep("step1", lambda ctx: True, lambda ctx: None)
        assert "step1" in str(step)
