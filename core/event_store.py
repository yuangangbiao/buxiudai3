# -*- coding: utf-8 -*-
"""事件存储 — 订单全生命周期事件持久化"""
import json, logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 可替换的连接工厂，测试时可注入 mock
_connection_factory = None


def _get_conn():
    """获取数据库连接。优先使用注入的工厂，否则回退到默认。"""
    if _connection_factory:
        return _connection_factory()
    from models.database import get_connection
    return get_connection()


def set_connection_factory(factory):
    """注入自定义连接工厂（用于测试）。传入 None 恢复默认。"""
    global _connection_factory
    _connection_factory = factory


class EventStore:
    """领域事件持久化。append → events 表，支持按聚合回放。"""

    @staticmethod
    def append(aggregate_type: str, aggregate_id: str, event_type: str, payload: dict) -> bool:
        """持久化一条领域事件"""
        payload_str = json.dumps(payload, ensure_ascii=False)
        if len(payload_str) > 10240:
            logger.error(f'[EventStore] payload超限: {len(payload_str)}字节, event={event_type}')
            return False
        try:
            conn = _get_conn()
            c = conn.cursor()
            c.execute(
                """INSERT INTO events (aggregate_type, aggregate_id, event_type, payload, occurred_at)
                   VALUES (%s, %s, %s, %s, %s)""",
                (aggregate_type, aggregate_id, event_type, payload_str, datetime.now())
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f'[EventStore] append失败: {e}')
            return False

    @staticmethod
    def get_events(aggregate_type: str, aggregate_id: str, limit: int = 100, offset: int = 0):
        """按聚合ID查询事件（时间正序，分页）"""
        try:
            conn = _get_conn()
            c = conn.cursor()
            c.execute(
                """SELECT id, aggregate_type, aggregate_id, event_type, payload, occurred_at
                   FROM events WHERE aggregate_type=%s AND aggregate_id=%s
                   ORDER BY occurred_at ASC LIMIT %s OFFSET %s""",
                (aggregate_type, aggregate_id, limit, offset)
            )
            rows = c.fetchall()
            conn.close()
            return [{'id': r[0], 'type': r[3], 'payload': json.loads(r[4]) if isinstance(r[4], str) else r[4],
                     'occurred_at': str(r[5])} for r in rows]
        except Exception as e:
            logger.error(f'[EventStore] query失败: {e}')
            return []

    @staticmethod
    def replay(aggregate_type: str, aggregate_id: str, handler) -> int:
        """回放事件：对每条事件调用 handler(event)"""
        events = EventStore.get_events(aggregate_type, aggregate_id, limit=10000)
        count = 0
        for ev in events:
            try:
                handler(ev)
                count += 1
            except Exception as e:
                logger.error(f'[EventStore] replay单条失败: {ev["id"]} {e}')
        return count
