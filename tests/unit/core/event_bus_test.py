# -*- coding: utf-8 -*-
"""Tests for core.event_bus — EventBus, Events, on_event, publish."""

import pytest
from core.event_bus import EventBus, Events, on_event, publish


@pytest.fixture(autouse=True)
def reset_bus():
    """Reset singleton before each test."""
    EventBus.reset()
    yield
    EventBus.reset()


# ── EventBus 单例 ──

def test_singleton():
    bus1 = EventBus()
    bus2 = EventBus()
    assert bus1 is bus2


# ── subscribe / publish ──

def test_subscribe_and_publish():
    received = []

    def handler(event, data):
        received.append((event, data))

    EventBus.subscribe("test:event", handler)
    EventBus.publish("test:event", {"key": "val"})

    assert len(received) == 1
    assert received[0] == ("test:event", {"key": "val"})


def test_publish_no_subscribers():
    """Publishing to an event with no subscribers should not raise."""
    EventBus.publish("nonexistent:event", 42)


def test_subscribe_duplicate_handler():
    """Same handler should only be added once."""
    calls = []

    def handler(event, data):
        calls.append(data)

    EventBus.subscribe("dup:event", handler)
    EventBus.subscribe("dup:event", handler)
    EventBus.publish("dup:event", 1)

    assert len(calls) == 1


# ── unsubscribe ──

def test_unsubscribe():
    calls = []

    def handler(event, data):
        calls.append(data)

    EventBus.subscribe("evt", handler)
    EventBus.unsubscribe("evt", handler)
    EventBus.publish("evt", 99)

    assert len(calls) == 0


def test_unsubscribe_not_subscribed():
    """Unsubscribing a handler that was never registered should not raise."""

    def handler(event, data):
        pass

    EventBus.unsubscribe("nothing", handler)  # should not raise


# ── clear ──

def test_clear_specific_event():
    EventBus.subscribe("a", lambda e, d: None)
    EventBus.subscribe("b", lambda e, d: None)
    EventBus.clear("a")
    assert EventBus.get_handlers("a") == []
    assert len(EventBus.get_handlers("b")) == 1


def test_clear_all():
    EventBus.subscribe("a", lambda e, d: None)
    EventBus.subscribe("b", lambda e, d: None)
    EventBus.clear()
    assert EventBus.get_handlers("a") == []
    assert EventBus.get_handlers("b") == []


# ── handler error isolation ──

def test_handler_exception_does_not_block_others(caplog):
    results = []

    def failing(e, d):
        raise ValueError("boom")

    def ok(e, d):
        results.append("ok")

    EventBus.subscribe("err:test", failing)
    EventBus.subscribe("err:test", ok)
    EventBus.publish("err:test", 1)

    assert results == ["ok"]
    assert "事件处理错误" in caplog.text


# ── get_handlers ──

def test_get_handlers_returns_names():
    def my_handler(e, d):
        pass

    EventBus.subscribe("evt", my_handler)
    names = EventBus.get_handlers("evt")
    assert names == ["my_handler"]


def test_get_handlers_empty():
    assert EventBus.get_handlers("unknown") == []


# ── Events 常量 ──

def test_events_constants():
    assert Events.ORDER_CREATED == "order:created"
    assert Events.ORDER_UPDATED == "order:updated"
    assert Events.ORDER_STATUS_CHANGED == "order:status_changed"
    assert Events.ORDER_DELETED == "order:deleted"

    assert Events.INVENTORY_INCREASED == "inventory:increased"
    assert Events.INVENTORY_DECREASED == "inventory:decreased"
    assert Events.INVENTORY_LOW_STOCK == "inventory:low_stock"

    assert Events.PROCESS_STARTED == "process:started"
    assert Events.PROCESS_COMPLETED == "process:completed"
    assert Events.PROCESS_REPORTED == "process:reported"

    assert Events.APP_STARTED == "app:started"
    assert Events.APP_CLOSED == "app:closed"
    assert Events.OPERATOR_LOGIN == "operator:login"
    assert Events.OPERATOR_LOGOUT == "operator:logout"


# ── on_event 装饰器 ──

def test_on_event_decorator():
    received = []

    @on_event("decorated:event")
    def my_handler(event, data):
        received.append((event, data))

    EventBus.publish("decorated:event", {"x": 1})
    assert len(received) == 1


# ── publish 便捷函数 ──

def test_publish_convenience_function():
    received = []

    def handler(event, data):
        received.append(data)

    EventBus.subscribe("test:conv", handler)
    publish("test:conv", 123)

    assert received == [123]


# ── reset ──

def test_reset_clears_all_state():
    EventBus.subscribe("x", lambda e, d: None)
    EventBus.reset()
    assert EventBus.get_handlers("x") == []

    # New instance should work fine after reset
    bus = EventBus()
    assert bus is not None
