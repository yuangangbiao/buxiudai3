# -*- coding: utf-8 -*-
"""
事件类型定义 - 统一管理系统中所有事件类型常量

使用方式：
    from core.events import EventType, EventBus

    EventBus.subscribe(EventType.PRODUCTION_CONFIRMED, handler_func)

    EventBus.publish(EventType.PRODUCTION_CONFIRMED, data={'order_id': 123})
"""

import logging

logger = logging.getLogger(__name__)


class EventType:
    """
    事件类型常量定义

    事件命名规范：
        - 使用冒号分隔命名空间：'entity:action'
        - entity: 实体名称（order, process, production, material, qc, inventory）
        - action: 操作类型（created, updated, confirmed, reported, completed, etc.）
    """

    # ==================== 订单相关事件 ====================
    ORDER_CREATED = 'order:created'
    ORDER_UPDATED = 'order:updated'
    ORDER_STATUS_CHANGED = 'order:status_changed'
    ORDER_CONFIRMED = 'order:confirmed'
    ORDER_SHIPPED = 'order:shipped'
    ORDER_DELETED = 'order:deleted'

    # ==================== 工序相关事件 ====================
    PROCESS_CREATED = 'process:created'
    PROCESS_STARTED = 'process:started'
    PROCESS_REPORTED = 'process:reported'
    PROCESS_COMPLETED = 'process:completed'
    PROCESS_STATUS_CHANGED = 'process:status_changed'
    PROCESS_DELETED = 'process:deleted'

    # ==================== 生产排产相关事件 ====================
    PRODUCTION_CONFIRMED = 'production:confirmed'
    PRODUCTION_UPDATED = 'production:updated'
    PRODUCTION_CANCELLED = 'production:cancelled'

    # ==================== 备料相关事件 ====================
    MATERIAL_PREPARED = 'material:prepared'
    MATERIAL_SELECTED = 'material:selected'
    MATERIAL_PUBLISHED = 'material:published'
    MATERIAL_LOW_STOCK = 'material:low_stock'

    # ==================== 质检相关事件 ====================
    QC_PASSED = 'qc:passed'
    QC_REJECTED = 'qc:rejected'
    QC_REQUESTED = 'qc:requested'

    # ==================== 库存相关事件 ====================
    INVENTORY_LOW = 'inventory:low'
    INVENTORY_ALERT = 'inventory:alert'
    INVENTORY_UPDATED = 'inventory:updated'

    # ==================== 任务发布相关事件 ====================
    TASK_PUBLISHED = 'task:published'
    TASK_ASSIGNED = 'task:assigned'
    TASK_COMPLETED = 'task:completed'
    TASK_TIMEOUT = 'task:timeout'

    # ==================== 系统相关事件 ====================
    SYSTEM_READY = 'system:ready'
    SYSTEM_ERROR = 'system:error'
    SYNC_COMPLETED = 'sync:completed'

    @classmethod
    def get_all_events(cls) -> list:
        """
        获取所有事件类型列表

        Returns:
            包含所有事件类型常量的列表
        """
        return [
            attr for attr in dir(cls)
            if not attr.startswith('_') and attr.isupper()
        ]

    @classmethod
    def is_valid_event(cls, event: str) -> bool:
        """
        检查事件类型是否有效

        Args:
            event: 事件名称或事件值

        Returns:
            True if valid, False otherwise
        """
        all_events = cls.get_all_events()
        return event in all_events or event in [
            getattr(cls, attr)
            for attr in dir(cls)
            if not attr.startswith('_') and attr.isupper()
        ]

    @classmethod
    def get_event_category(cls, event: str) -> str:
        """
        获取事件类别

        Args:
            event: 事件名称

        Returns:
            事件类别（如 'order', 'process', 'production' 等）
        """
        if ':' in event:
            return event.split(':')[0]
        return 'unknown'


class EventData:
    """
    事件数据包装类

    用于标准化事件数据的格式，确保事件处理器接收到一致的数据结构
    """

    def __init__(self, event: str, data: dict = None):
        """
        初始化事件数据

        Args:
            event: 事件类型
            data: 事件相关数据
        """
        self.event = event
        self.data = data or {}
        self.timestamp = None

    def get(self, key: str, default=None):
        """获取事件数据中的值"""
        return self.data.get(key, default)

    def set(self, key: str, value) -> None:
        """设置事件数据中的值"""
        self.data[key] = value

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'event': self.event,
            'data': self.data,
            'timestamp': self.timestamp
        }

    def __repr__(self) -> str:
        return f"EventData(event='{self.event}', data={self.data})"


def create_event(event: str, **kwargs) -> EventData:
    """
    创建事件数据对象的便捷函数

    Args:
        event: 事件类型
        **kwargs: 事件数据键值对

    Returns:
        EventData 对象

    Example:
        event_data = create_event(
            EventType.ORDER_CREATED,
            order_id=123,
            order_no='WB-2025-0501'
        )
    """
    return EventData(event, kwargs)
