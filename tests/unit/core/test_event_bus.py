# -*- coding: utf-8 -*-
r"""core/event_bus.py 的集成测试。

真源码行为(已读 d:\yuan\不锈钢网带跟单3.0\core\event_bus.py 验证):
- EventBus 是单例(__new__ + _lock 双重检查),每个实例独立 _handlers(defaultdict(list))
- 类方法 reset() 重置单例(测试专用),_handlers 也重置
- subscribe/unsubscribe/publish/clear/get_handlers 都是 classmethod
- subscribe 重复 handler 不会重复添加
- publish 时 handlers 抛异常被 logger.error 捕获,不阻断其他 handlers
- Events 预定义 12 个事件常量(ORDER_CREATED 等)
- on_event 装饰器,publish 顶层函数
"""
import pytest

from core.event_bus import EventBus, Events, on_event, publish


@pytest.fixture(autouse=True)
def _reset_event_bus():
    r"""每个测试前后都 reset EventBus 单例,避免污染。"""
    EventBus.reset()
    yield
    EventBus.reset()


def test_event_bus_is_singleton():
    r"""EventBus 多次 __new__ 必须返同一实例(__new__ 单例)。"""
    a = EventBus()
    b = EventBus()
    assert a is b


def test_reset_clears_singleton():
    r"""reset() 后,新的 EventBus() 是新实例,handlers 空。"""
    bus1 = EventBus()
    assert len(bus1.get_handlers("any_event")) == 0

    EventBus.reset()
    bus2 = EventBus()
    assert bus1 is not bus2
    assert len(bus2.get_handlers("any_event")) == 0


def test_subscribe_adds_handler():
    r"""subscribe(event, handler) 后 get_handlers 必须含 handler.__name__。"""
    def handler(event, data):
        pass

    EventBus.subscribe("test_event", handler)
    assert "handler" in EventBus.get_handlers("test_event")


def test_subscribe_no_duplicate():
    r"""重复 subscribe 同一 handler 不会重复添加(源码 line 49-50 去重)。"""
    def handler(event, data):
        pass

    EventBus.subscribe("e", handler)
    EventBus.subscribe("e", handler)
    EventBus.subscribe("e", handler)
    assert EventBus.get_handlers("e") == ["handler"]


def test_unsubscribe_removes_handler():
    r"""unsubscribe(event, handler) 后 handler 必须从列表中移除。"""
    def handler(event, data):
        pass

    EventBus.subscribe("e", handler)
    assert "handler" in EventBus.get_handlers("e")

    EventBus.unsubscribe("e", handler)
    assert "handler" not in EventBus.get_handlers("e")


def test_unsubscribe_nonexistent_handler_does_not_raise():
    r"""unsubscribe 不存在的 handler 不抛异常。"""
    def handler(event, data):
        pass

    EventBus.unsubscribe("nonexistent_event", handler)
    EventBus.unsubscribe("any_event", handler)


def test_publish_calls_handler_with_event_and_data():
    r"""publish(event, data) 必须调 handler(event, data)。"""
    received = []
    def handler(event, data):
        received.append((event, data))

    EventBus.subscribe("order:created", handler)
    EventBus.publish("order:created", {"order_no": "GO-001"})
    assert received == [("order:created", {"order_no": "GO-001"})]


def test_publish_no_handlers_does_not_raise():
    r"""publish 没订阅者时不抛异常。"""
    EventBus.publish("no_subscribers", "data")


def test_publish_handler_exception_does_not_break_others():
    r"""publish 时某个 handler 抛异常,被 logger.error 捕获,不阻断其他 handlers。"""
    received = []
    def bad_handler(event, data):
        raise RuntimeError("handler-boom")
    def good_handler(event, data):
        received.append((event, data))

    EventBus.subscribe("e", bad_handler)
    EventBus.subscribe("e", good_handler)
    EventBus.publish("e", {"x": 1})
    assert received == [("e", {"x": 1})]


def test_clear_specific_event():
    r"""clear(event) 只清指定 event 的 handlers,其他 event 不受影响。"""
    def h(event, data):
        pass

    EventBus.subscribe("e1", h)
    EventBus.subscribe("e2", h)
    EventBus.clear("e1")
    assert EventBus.get_handlers("e1") == []
    assert "h" in EventBus.get_handlers("e2")


def test_clear_all_events():
    r"""clear() 不传 event 参数,清空所有 handlers。"""
    def h(event, data):
        pass

    EventBus.subscribe("e1", h)
    EventBus.subscribe("e2", h)
    EventBus.clear()
    assert EventBus.get_handlers("e1") == []
    assert EventBus.get_handlers("e2") == []


def test_get_handlers_no_event_returns_empty():
    r"""get_handlers 未订阅 event 返 []。"""
    assert EventBus.get_handlers("never_subscribed") == []


def test_events_order_constants():
    r"""Events 订单相关 4 个事件常量必须存在。"""
    assert Events.ORDER_CREATED == "order:created"
    assert Events.ORDER_UPDATED == "order:updated"
    assert Events.ORDER_STATUS_CHANGED == "order:status_changed"
    assert Events.ORDER_DELETED == "order:deleted"


def test_events_inventory_constants():
    r"""Events 库存相关 3 个事件常量必须存在。"""
    assert Events.INVENTORY_INCREASED == "inventory:increased"
    assert Events.INVENTORY_DECREASED == "inventory:decreased"
    assert Events.INVENTORY_LOW_STOCK == "inventory:low_stock"


def test_events_process_constants():
    r"""Events 工序相关 3 个事件常量必须存在。"""
    assert Events.PROCESS_STARTED == "process:started"
    assert Events.PROCESS_COMPLETED == "process:completed"
    assert Events.PROCESS_REPORTED == "process:reported"


def test_events_system_constants():
    r"""Events 系统相关 4 个事件常量必须存在。"""
    assert Events.APP_STARTED == "app:started"
    assert Events.APP_CLOSED == "app:closed"
    assert Events.OPERATOR_LOGIN == "operator:login"
    assert Events.OPERATOR_LOGOUT == "operator:logout"


def test_on_event_decorator_subscribes_function():
    r"""on_event 装饰器自动 subscribe handler 到 EventBus。"""
    received = []
    @on_event("order:created")
    def handle_order_created(event, data):
        received.append((event, data))

    assert "handle_order_created" in EventBus.get_handlers("order:created")
    EventBus.publish("order:created", {"order_no": "GO-001"})
    assert received == [("order:created", {"order_no": "GO-001"})]


def test_on_event_decorator_returns_function_unchanged():
    r"""on_event 装饰器必须返原函数(不被替换),以便继续调用。"""
    @on_event("any_event")
    def my_handler(event, data):
        return "ok"

    assert callable(my_handler)
    assert my_handler("any_event", None) == "ok"


def test_publish_top_level_function_calls_eventbus_publish():
    r"""顶层 publish(event, data) 是 EventBus.publish 的封装。"""
    received = []
    def handler(event, data):
        received.append(data)

    EventBus.subscribe("e", handler)
    publish("e", {"x": 42})
    assert received == [{"x": 42}]


def test_multiple_handlers_receive_same_event():
    r"""多个 handler 订阅同一 event,全部被调用(顺序按 subscribe 顺序)。"""
    received = []
    EventBus.subscribe("e", lambda evt, data: received.append("h1"))
    EventBus.subscribe("e", lambda evt, data: received.append("h2"))
    EventBus.subscribe("e", lambda evt, data: received.append("h3"))
    EventBus.publish("e", None)
    assert received == ["h1", "h2", "h3"]
