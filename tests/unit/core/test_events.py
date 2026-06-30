# -*- coding: utf-8 -*-
"""
core/events.py 单元测试
"""

import pytest

from core.events import EventType, EventData, create_event


class TestEventType:

    def test_order_events_exist(self):
        """验证订单事件常量存在"""
        assert hasattr(EventType, 'ORDER_CREATED')
        assert hasattr(EventType, 'ORDER_CONFIRMED')
        assert hasattr(EventType, 'ORDER_SHIPPED')
        assert hasattr(EventType, 'ORDER_DELETED')

    def test_process_events_exist(self):
        """验证工序事件常量存在"""
        assert hasattr(EventType, 'PROCESS_STARTED')
        assert hasattr(EventType, 'PROCESS_REPORTED')
        assert hasattr(EventType, 'PROCESS_COMPLETED')

    def test_production_events_exist(self):
        """验证生产事件常量存在"""
        assert hasattr(EventType, 'PRODUCTION_CONFIRMED')
        assert hasattr(EventType, 'PRODUCTION_UPDATED')
        assert hasattr(EventType, 'PRODUCTION_CANCELLED')

    def test_material_events_exist(self):
        """验证备料事件常量存在"""
        assert hasattr(EventType, 'MATERIAL_PREPARED')
        assert hasattr(EventType, 'MATERIAL_SELECTED')
        assert hasattr(EventType, 'MATERIAL_PUBLISHED')

    def test_qc_events_exist(self):
        """验证质检事件常量存在"""
        assert hasattr(EventType, 'QC_PASSED')
        assert hasattr(EventType, 'QC_REJECTED')
        assert hasattr(EventType, 'QC_REQUESTED')

    def test_inventory_events_exist(self):
        """验证库存事件常量存在"""
        assert hasattr(EventType, 'INVENTORY_LOW')
        assert hasattr(EventType, 'INVENTORY_ALERT')
        assert hasattr(EventType, 'INVENTORY_UPDATED')

    def test_event_value_format(self):
        """验证事件值格式正确（使用冒号分隔）"""
        events = [
            EventType.ORDER_CREATED,
            EventType.PRODUCTION_CONFIRMED,
            EventType.MATERIAL_PREPARED,
            EventType.QC_PASSED
        ]
        for event in events:
            assert ':' in event

    def test_get_event_category(self):
        """验证事件类别提取"""
        assert EventType.get_event_category('order:created') == 'order'
        assert EventType.get_event_category('production:confirmed') == 'production'
        assert EventType.get_event_category('material:prepared') == 'material'
        assert EventType.get_event_category('qc:passed') == 'qc'
        assert EventType.get_event_category('inventory:low') == 'inventory'
        assert EventType.get_event_category('unknown_event') == 'unknown'

    def test_is_valid_event(self):
        """验证事件有效性检查"""
        assert EventType.is_valid_event(EventType.ORDER_CREATED)
        assert EventType.is_valid_event(EventType.PRODUCTION_CONFIRMED)
        assert not EventType.is_valid_event('invalid:event')
        assert not EventType.is_valid_event('not_an_event')

    def test_get_all_events(self):
        """验证获取所有事件列表"""
        events = EventType.get_all_events()
        assert isinstance(events, list)
        assert len(events) > 10
        assert 'ORDER_CREATED' in events
        assert 'PRODUCTION_CONFIRMED' in events
        assert 'MATERIAL_PREPARED' in events


class TestEventData:

    def test_event_data_init(self):
        """验证事件数据初始化"""
        data = EventData('order:created', {'order_id': 123})
        assert data.event == 'order:created'
        assert data.data['order_id'] == 123

    def test_event_data_get(self):
        """验证事件数据获取"""
        data = EventData('order:created', {'order_id': 123, 'order_no': 'WB001'})
        assert data.get('order_id') == 123
        assert data.get('order_no') == 'WB001'
        assert data.get('nonexistent') is None
        assert data.get('nonexistent', 'default') == 'default'

    def test_event_data_set(self):
        """验证事件数据设置"""
        data = EventData('order:created', {})
        data.set('order_id', 456)
        assert data.data['order_id'] == 456

    def test_event_data_to_dict(self):
        """验证事件数据转字典"""
        data = EventData('order:created', {'order_id': 123})
        result = data.to_dict()
        assert isinstance(result, dict)
        assert result['event'] == 'order:created'
        assert result['data']['order_id'] == 123


class TestCreateEvent:

    def test_create_event_basic(self):
        """验证创建事件基本功能"""
        event = create_event(EventType.ORDER_CREATED, order_id=123)
        assert event.event == EventType.ORDER_CREATED
        assert event.get('order_id') == 123

    def test_create_event_multiple_params(self):
        """验证创建事件多参数"""
        event = create_event(
            EventType.PRODUCTION_CONFIRMED,
            order_id=1,
            production_id=2,
            process_id=3
        )
        assert event.get('order_id') == 1
        assert event.get('production_id') == 2
        assert event.get('process_id') == 3

    def test_create_event_empty_data(self):
        """验证创建事件空数据"""
        event = create_event(EventType.ORDER_CREATED)
        assert event.event == EventType.ORDER_CREATED
        assert event.data == {}
