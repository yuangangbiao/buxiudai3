# -*- coding: utf-8 -*-
"""
订单状态 SSOT (Single Source of Truth) 契约模块

[规范 v0.2 - 2026-06-16]
- 唯一写入入口: update_order_status()
- 唯一读取入口: get_order_status()
- 乐观锁防并发: last_status_update_at 字段
- 来源标识: 写入时必须携带 source
- 灰度开关: USE_SSOT_STATUS (core/_config_domain.py)
"""
import logging
import os
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List
from models.database import get_connection

USE_SSOT_STATUS = os.getenv('USE_SSOT_STATUS', 'true').lower() != 'false'

_ssot_stats = {
    'update_total': 0,
    'update_success': 0,
    'update_conflict': 0,
    'update_not_found': 0,
    'update_error': 0,
    'update_disabled': 0,
    'get_total': 0,
    'batch_get_total': 0,
    'eventbus_publish': 0,
    'eventbus_unavailable': 0,
}


def get_ssot_stats() -> Dict[str, int]:
    return dict(_ssot_stats)


def reset_ssot_stats() -> None:
    for k in _ssot_stats:
        _ssot_stats[k] = 0


try:
    from core.event_bus import publish as _publish_event, Events
    _EVENTBUS_AVAILABLE = True
except ImportError:
    _EVENTBUS_AVAILABLE = False
    _publish_event = None
    Events = None

logger = logging.getLogger(__name__)

LOG_ORDER_NO_MAX_LEN = 64


def _sanitize_for_log(order_no) -> str:
    if order_no is None:
        return 'EMPTY'
    s = str(order_no)
    if len(s) > LOG_ORDER_NO_MAX_LEN:
        s = s[:LOG_ORDER_NO_MAX_LEN] + '...(truncated)'
    return s.replace('\n', '\\n').replace('\r', '\\r')


STATUS_TO_STEP = {
    'created': 0,
    'pending': 0,
    'published': 1,
    'scheduled': 2,
    'confirmed': 3,
    'in_production': 4,
    'reported': 5,
    'qc_passed': 6,
    'completed': 7,
    'cancelled': -1,
}

MYSQL_STATUS_TO_KEY = {
    '已发布': 'published',
    '已排产': 'scheduled',
    '生产中': 'in_production',
    '质检中': 'reported',
    '质检通过': 'qc_passed',
    '已完成': 'completed',
    '已取消': 'cancelled',
}


def mysql_status_to_key(mysql_status: str) -> str:
    if not mysql_status:
        return 'pending'
    return MYSQL_STATUS_TO_KEY.get(mysql_status, 'pending')


def infer_current_step_from_status(status: str) -> int:
    return STATUS_TO_STEP.get(status, 0)


def update_order_status(
    order_no: str,
    new_status: str,
    expected_last_update_at: Optional[datetime] = None,
    source: str = 'ssot_unknown',
) -> Tuple[bool, str]:
    _ssot_stats['update_total'] += 1

    if not USE_SSOT_STATUS:
        _ssot_stats['update_disabled'] += 1
        return (False, 'SSOT_DISABLED')

    try:
        conn = get_connection()
        cursor = conn.cursor()

        current_step = infer_current_step_from_status(new_status)

        if expected_last_update_at is not None:
            cursor.execute(
                """
                UPDATE orders
                SET status = %s,
                    current_step = %s,
                    last_status_update_at = %s,
                    updated_at = %s
                WHERE order_no = %s
                  AND last_status_update_at = %s
                """,
                (new_status, current_step, datetime.now(), datetime.now(),
                 order_no, expected_last_update_at)
            )
        else:
            cursor.execute(
                """
                UPDATE orders
                SET status = %s,
                    current_step = %s,
                    last_status_update_at = COALESCE(last_status_update_at, %s),
                    updated_at = %s
                WHERE order_no = %s
                """,
                (new_status, current_step, datetime.now(), datetime.now(), order_no)
            )

        if cursor.rowcount == 0 and expected_last_update_at is not None:
            cursor.execute(
                "SELECT id FROM orders WHERE order_no = %s", (order_no,))
            if cursor.fetchone() is None:
                _ssot_stats['update_not_found'] += 1
                conn.close()
                return (False, 'NOT_FOUND')
            else:
                _ssot_stats['update_conflict'] += 1
                conn.close()
                return (False, 'CONFLICT')

        conn.commit()
        conn.close()

        _ssot_stats['update_success'] += 1

        logger.info(
            f'[SSOT] 状态更新成功 order_no={_sanitize_for_log(order_no)} '
            f'status={new_status} step={current_step} source={source}'
        )

        if _EVENTBUS_AVAILABLE:
            try:
                _publish_event(Events.ORDER_STATUS_CHANGED, {
                    'order_no': order_no,
                    'new_status': new_status,
                    'current_step': current_step,
                    'source': source,
                })
                _ssot_stats['eventbus_publish'] += 1
            except Exception as e:
                logger.warning(f'[SSOT] EventBus publish 失败: {e}')
        else:
            _ssot_stats['eventbus_unavailable'] += 1

        return (True, 'OK')

    except Exception as e:
        _ssot_stats['update_error'] += 1
        logger.error(f'[SSOT] 状态更新失败 order_no={_sanitize_for_log(order_no)}: {e}')
        try:
            conn.close()
        except Exception:
            pass
        return (False, str(e))


def get_order_status(order_no: str) -> Optional[Dict[str, Any]]:
    _ssot_stats['get_total'] += 1

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT order_no, status, current_step,
                   last_status_update_at, updated_at
            FROM orders
            WHERE order_no = %s AND is_deleted = 0
            """,
            (order_no,)
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        current_step = row['current_step'] or 0
        if current_step == 0 and row['status']:
            current_step = infer_current_step_from_status(row['status'])

        return {
            'order_no': row['order_no'],
            'status': row['status'],
            'current_step': current_step,
            'last_status_update_at': row['last_status_update_at'] or row['updated_at'],
            'source': 'ssot',
        }

    except Exception as e:
        logger.error(f'[SSOT] 状态读取失败 order_no={_sanitize_for_log(order_no)}: {e}')
        try:
            conn.close()
        except Exception:
            pass
        return None


def batch_get_order_status(order_nos: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
    if not order_nos:
        return {}
    _ssot_stats['batch_get_total'] += 1

    try:
        conn = get_connection()
        cursor = conn.cursor()

        placeholders = ','.join(['%s'] * len(order_nos))
        cursor.execute(
            f"""
            SELECT order_no, status, current_step,
                   last_status_update_at, updated_at
            FROM orders
            WHERE order_no IN ({placeholders}) AND is_deleted = 0
            """,
            tuple(order_nos)
        )
        rows = cursor.fetchall()
        conn.close()

        result = {}
        for row in rows:
            result[row['order_no']] = {
                'order_no': row['order_no'],
                'status': row['status'],
                'current_step': row['current_step'] or infer_current_step_from_status(row['status']),
                'last_status_update_at': row['last_status_update_at'] or row['updated_at'],
                'source': 'ssot',
            }
        for no in order_nos:
            if no not in result:
                result[no] = None

        return result

    except Exception as e:
        logger.error(f'[SSOT] 批量状态读取失败 order_nos={[_sanitize_for_log(no) for no in order_nos]}: {e}')
        try:
            conn.close()
        except Exception:
            pass
        return {no: None for no in order_nos}
