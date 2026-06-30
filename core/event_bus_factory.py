# -*- coding: utf-8 -*-
"""事件总线工厂——根据环境变量选择 inprocess / redis"""
import os
import logging

logger = logging.getLogger(__name__)


def create_event_bus():
    """创建事件总线实例。

    根据环境变量 EVENT_BUS_BACKEND 选择后端：
    - 'redis': 使用 Redis Pub/Sub 跨进程事件总线
    - 其他/默认: 使用进程内单例事件总线（兼容现有 sync.event_bus.EventBus）

    Returns:
        具有 publish(event, data) 方法的事件总线实例
    """
    backend = os.getenv('EVENT_BUS_BACKEND', 'inprocess')
    if backend == 'redis':
        try:
            from core.redis_event_bus import RedisEventBus
            host = os.getenv('REDIS_HOST', 'localhost')
            port = int(os.getenv('REDIS_PORT', 6379))
            bus = RedisEventBus(host=host, port=port)
            logger.info("[EventBusFactory] Redis 模式: %s:%s", host, port)
            return bus
        except Exception as e:
            logger.warning("[EventBusFactory] Redis 不可用，降级 inprocess: %s", e)
    try:
        from sync.event_bus import EventBus as SyncEventBus
        return SyncEventBus.get()
    except ImportError:
        from core.event_bus import EventBus
        return EventBus()
