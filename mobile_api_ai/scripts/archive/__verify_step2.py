# -*- coding: utf-8 -*-
"""验证步骤5：EventBus单例 + 发布/订阅"""
import sys
sys.path.insert(0, '.')
from sync.event_bus import EventBus

# 测试单例模式
bus = EventBus.get()
bus2 = EventBus.get()
assert bus is bus2, '单例模式失败'
print(f'[OK] EventBus 单例: id={id(bus)}')

# 测试发布/订阅
logs = []
def test_handler(event_type, data):
    logs.append(data)

bus.subscribe('test.event', test_handler)
bus.publish('test.event', {'msg': 'hello'})
assert len(logs) == 1, f'预期1个事件，收到{len(logs)}个'
assert logs[0]['msg'] == 'hello', f'数据不匹配: {logs[0]}'
print(f'[OK] EventBus 发布/订阅: 收到{len(logs)}个事件, msg={logs[0]["msg"]}')
