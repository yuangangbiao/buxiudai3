# -*- coding: utf-8 -*-
"""
Outbox 写工具 — 将变更事件写入 steel_belt.sync_outbox

使用方式（在任意写操作后调用）:
    from outbox_writer import publish_event
    publish_event('orders', 'create', order_id, {'order_no': 'ORD-001', ...})

数据流:
    业务写 steel_belt ──同步写── sync_outbox ──worker 轮询──→ dispatch_center (5003)
"""
import json
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# sync_outbox 表 DDL（可由 caller 初始化）
_OUTBOX_DDL = """
CREATE TABLE IF NOT EXISTS sync_outbox (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    event_id       VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '幂等唯一ID',
    action         VARCHAR(64)  NOT NULL COMMENT '事件类型: {table}.{op}',
    target_db      VARCHAR(32)  NOT NULL DEFAULT 'dispatch_center' COMMENT '目标服务',
    record_id      VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '业务记录ID',
    payload        JSON         NOT NULL COMMENT '变更数据',
    status         VARCHAR(16)  NOT NULL DEFAULT 'pending' COMMENT 'pending|processed|dead',
    retry_count    INT          NOT NULL DEFAULT 0,
    max_retries    INT          NOT NULL DEFAULT 5,
    last_error     TEXT,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at   DATETIME,
    INDEX idx_status_action (status, action),
    INDEX idx_event_id (event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='变更事件发件箱'
"""


def ensure_outbox_table():
    """确保 sync_outbox 表存在（幂等）"""
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                c.execute(_OUTBOX_DDL)
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        logger.warning('[outbox_writer] 建表失败: %s', e)


def publish_event(action: str, record_id: str, payload: dict,
                  target_db: str = 'dispatch_center', max_retries: int = 5) -> bool:
    """将业务变更写入 outbox 表

    Args:
        action:     事件类型，格式 '{table}.{op}'，如 'orders.create'
        record_id:  业务记录主键（字符串，兼容 varchar id）
        payload:     变更数据 dict
        target_db:   目标服务标识（默认 dispatch_center）
        max_retries: 最大重试次数

    Returns:
        True=写入成功，False=写入失败（不阻塞主业务）
    """
    try:
        from utils.trace import get_trace_id
        trace_id = get_trace_id() or ''
    except Exception:
        trace_id = ''

    try:
        conn = _get_conn()
        try:
            with conn.cursor() as c:
                c.execute(_OUTBOX_DDL)  # 建表幂等
                c.execute("""
                    INSERT INTO sync_outbox
                    (event_id, action, target_db, record_id, payload, status, retry_count, max_retries, created_at)
                    VALUES (%s, %s, %s, %s, %s, 'pending', 0, %s, %s)
                """, (
                    f'{action}:{record_id}:{uuid.uuid4().hex[:8]}',
                    action,
                    target_db,
                    str(record_id),
                    json.dumps(payload, ensure_ascii=False, default=str),
                    max_retries,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ))
            conn.commit()
            logger.debug('[outbox] 写入: action=%s, record_id=%s', action, record_id)
            return True
        finally:
            conn.close()
    except Exception as e:
        logger.warning('[outbox] 写入失败: action=%s, record_id=%s, err=%s', action, record_id, e)
        return False


# ── 内部 ──

def _get_conn():
    """获取 steel_belt 连接（复用已有连接池）"""
    from db.steelbelt_pool import get_conn
    return get_conn()


def get_outbox_stats() -> dict:
    """[P1-10 修复 2026-06-24] outbox 队列统计 - 用于监控积压

    Returns:
        {
            'pending': N,    # 待处理（积压）
            'processed': N,  # 已处理
            'dead': N,       # 死信
            'oldest_pending_age_seconds': N  # 最老 pending 事件存在时长
        }
    """
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            # 各状态计数
            cur.execute("""
                SELECT status, COUNT(*) AS cnt
                FROM sync_outbox
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                GROUP BY status
            """)
            counts = {row['status']: row['cnt'] for row in cur.fetchall()}

            # 最老 pending 事件存在时长（秒）
            cur.execute("""
                SELECT TIMESTAMPDIFF(SECOND, MIN(created_at), NOW()) AS age
                FROM sync_outbox
                WHERE status = 'pending'
            """)
            row = cur.fetchone()
            oldest_age = row['age'] if row and row['age'] else 0
        conn.close()
        return {
            'pending': counts.get('pending', 0),
            'processed': counts.get('processed', 0),
            'dead': counts.get('dead', 0),
            'oldest_pending_age_seconds': int(oldest_age),
        }
    except Exception as e:
        logger.error('[outbox] 统计查询失败: %s', e)
        return {'pending': -1, 'processed': -1, 'dead': -1, 'oldest_pending_age_seconds': -1, 'error': '操作失败，请稍后重试'[:200]}
