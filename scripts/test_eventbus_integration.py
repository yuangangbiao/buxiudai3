# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

PASS, FAIL = 0, 0

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  ✓ {name}")
    except Exception as e:
        FAIL += 1
        print(f"  ✗ {name}: {e}")

def main():
    global PASS, FAIL
    print("=" * 60)
    print("EventBus 集成验证测试")
    print("=" * 60)

    print("\n[1] EventType 常量检查")
    def t1():
        from core.events import EventType
        for attr, val in [("PROCESS_CREATED","process:created"),("PROCESS_STARTED","process:started"),
                          ("PROCESS_REPORTED","process:reported"),("PROCESS_COMPLETED","process:completed"),
                          ("PROCESS_DELETED","process:deleted")]:
            assert getattr(EventType, attr) == val, f"{attr} != {val}"
    test("所有工序事件常量存在且值正确", t1)

    print("\n[2] EventBus 发布-订阅")
    def t2():
        from core.event_bus import EventBus
        bus = EventBus()
        r = []
        bus.subscribe('test', lambda d: r.append(d))
        bus.publish('test', {'x': 1})
        assert len(r) == 1 and r[0] == {'x': 1}
        bus.clear()
    test("publish/subscribe 正常", t2)

    def t3():
        from core.event_bus import EventBus
        bus = EventBus()
        r = []
        def h(d): r.append(d)
        bus.subscribe('unsub', h)
        bus.publish('unsub', {'n': 1})
        bus.unsubscribe('unsub', h)
        bus.publish('unsub', {'n': 2})
        assert len(r) == 1
        bus.clear()
    test("unsubscribe 后不再收到事件", t3)

    def t4():
        from core.event_bus import EventBus
        bus = EventBus()
        r = []
        def h1(d): r.append(('h1', d))
        def h2(d): r.append(('h2', d))
        bus.subscribe('multi', h1)
        bus.subscribe('multi', h2)
        bus.publish('multi', {'k': 'v'})
        assert len(r) == 2
        bus.clear()
    test("多订阅者均能收到", t4)

    def t5():
        from core.event_bus import EventBus
        bus = EventBus()
        r = []
        def h(d): r.append(d)
        bus.subscribe('clear', h)
        bus.clear()
        bus.publish('clear', {'x': 1})
        assert len(r) == 0
    test("clear 后不再触发", t5)

    print("\n[3] ContainerEventListener 初始化")
    def t6():
        from container_event_listener import init_container_listener, get_container_listener
        init_container_listener()
        assert get_container_listener() is not None
    test("init_container_listener 正常", t6)

    print("\n[4] 事件发布不抛异常")
    def t7():
        from container_event_listener import init_container_listener
        init_container_listener()
        from core.event_bus import EventBus
        EventBus.publish('process:created', {'process_id':999,'order_id':888,'production_id':777,'process_name':'测试','worker':'测试','process_seq':1})
    test("process:created 发布不抛异常", t7)

    print("\n" + "=" * 60)
    print(f"结果: {PASS} 通过, {FAIL} 失败, 共 {PASS+FAIL} 项")
    print("=" * 60)
    return 1 if FAIL else 0

if __name__ == '__main__':
    sys.exit(main())
