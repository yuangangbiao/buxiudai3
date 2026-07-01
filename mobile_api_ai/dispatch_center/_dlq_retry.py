# -*- coding: utf-8 -*-
"""
[v3.7.0] DLQ (Dead Letter Queue) retry worker

背景:
    业务消息发送失败后会写入 dlq 表, 之前没有自动重试机制
    需要 DLQ retry worker 定期扫描并重试

特性:
    - 幂等启动（多次启动只生效一次）
    - 指数退避: 1s → 2s → 4s → 8s → 16s
    - 最大重试 5 次, 超过后标记为 poison message
    - 失败告警 (logger.critical)
    - 优雅停止 (threading.Event)

调用:
    from dispatch_center._dlq_retry import start_dlq_retry_worker
    start_dlq_retry_worker()  # 在 standalone_dispatch_server.py 启动时调用
"""
import os
import time
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── 配置 ──
_DLQ_RETRY_INTERVAL = int(os.environ.get('DLQ_RETRY_INTERVAL', '30'))  # 30 秒
_DLQ_BATCH_SIZE = int(os.environ.get('DLQ_BATCH_SIZE', '100'))
_DLQ_MAX_RETRIES = int(os.environ.get('DLQ_MAX_RETRIES', '5'))

# 指数退避基数 (秒)
_DLQ_BACKOFF_BASE = 2

# 状态
_DLQ_WORKER_STARTED = False
_DLQ_WORKER_LOCK = threading.Lock()
_DLQ_STOP_EVENT = threading.Event()
_DLQ_LAST_RUN = {'ts': 0, 'success': 0, 'failed': 0, 'poisoned': 0}
_DLQ_STATS = {
    'total_retries': 0,
    'total_success': 0,
    'total_failed': 0,
    'total_poisoned': 0,
}


def start_dlq_retry_worker() -> bool:
    """启动 DLQ retry worker（幂等，只能启动一次）

    Returns:
        bool: True=本次启动了, False=之前已启动
    """
    global _DLQ_WORKER_STARTED
    with _DLQ_WORKER_LOCK:
        if _DLQ_WORKER_STARTED:
            return False
        _DLQ_WORKER_STARTED = True
        _DLQ_STOP_EVENT.clear()

    t = threading.Thread(
        target=_dlq_retry_loop,
        name='DLQRetryWorker',
        daemon=True,
    )
    t.start()
    logger.info(
        f'[dlq_retry] worker 已启动, interval={_DLQ_RETRY_INTERVAL}s, '
        f'batch={_DLQ_BATCH_SIZE}, max_retries={_DLQ_MAX_RETRIES}'
    )
    return True


def stop_dlq_retry_worker() -> bool:
    """停止 DLQ retry worker

    Returns:
        bool: True=成功停止, False=未启动
    """
    global _DLQ_WORKER_STARTED
    with _DLQ_WORKER_LOCK:
        if not _DLQ_WORKER_STARTED:
            return False
        _DLQ_WORKER_STARTED = False
    _DLQ_STOP_EVENT.set()
    logger.info('[dlq_retry] worker 已发送停止信号')
    return True


def get_dlq_stats() -> dict:
    """获取 DLQ retry worker 统计信息（供监控/调试）"""
    return {
        'started': _DLQ_WORKER_STARTED,
        'last_run': _DLQ_LAST_RUN.copy(),
        'stats': _DLQ_STATS.copy(),
        'config': {
            'interval': _DLQ_RETRY_INTERVAL,
            'batch_size': _DLQ_BATCH_SIZE,
            'max_retries': _DLQ_MAX_RETRIES,
        },
    }


def _dlq_retry_loop() -> None:
    """主循环（每 _DLQ_RETRY_INTERVAL 秒一次）"""
    while not _DLQ_STOP_EVENT.is_set():
        # 等待支持中断
        if _DLQ_STOP_EVENT.wait(_DLQ_RETRY_INTERVAL):
            break

        try:
            _dlq_retry_once()
        except Exception:
            # [Q-B7 修复 2026-06-25] 用 logger.exception 自动带堆栈
            logger.exception('[dlq_retry] 重试失败')


def _dlq_retry_once() -> int:
    """单次执行

    Returns:
        int: 成功重试的消息数
    """
    # 1. 查询待重试消息
    records = _fetch_pending_dlq_records(limit=_DLQ_BATCH_SIZE)
    if not records:
        return 0

    success_count = 0
    failed_count = 0
    poisoned_count = 0

    for record in records:
        try:
            if _try_retry_one(record):
                success_count += 1
            else:
                failed_count += 1
        except Exception:
            # [Q-B7 修复] 用 logger.exception 自动带堆栈
            logger.exception(
                f'[dlq_retry] 单条处理失败 id={record.get("id")}'
            )
            failed_count += 1
        finally:
            # 检查是否 poison
            if record.get('retry_count', 0) >= _DLQ_MAX_RETRIES:
                _mark_as_poison(record['id'])
                poisoned_count += 1

    # 更新统计
    _DLQ_LAST_RUN['ts'] = int(time.time())
    _DLQ_LAST_RUN['success'] = success_count
    _DLQ_LAST_RUN['failed'] = failed_count
    _DLQ_LAST_RUN['poisoned'] = poisoned_count

    _DLQ_STATS['total_retries'] += len(records)
    _DLQ_STATS['total_success'] += success_count
    _DLQ_STATS['total_failed'] += failed_count
    _DLQ_STATS['total_poisoned'] += poisoned_count

    if success_count or failed_count or poisoned_count:
        logger.info(
            f'[dlq_retry] 批次: total={len(records)} '
            f'success={success_count} failed={failed_count} poisoned={poisoned_count}'
        )

    return success_count


def _fetch_pending_dlq_records(limit: int = 100) -> list:
    """从 dlq 表查询待重试记录

    筛选条件:
        - next_retry_at IS NULL OR next_retry_at <= NOW()
        - retry_count < _DLQ_MAX_RETRIES
        - status != 'poisoned'

    Returns:
        list: 记录列表
    """
    try:
        from ._db import _get_mysql_connection
    except ImportError:
        logger.warning('[dlq_retry] 无法导入 _db，跳过本次重试')
        return []

    sql = """
        SELECT id, payload, retry_count, next_retry_at, error_msg, status
        FROM dlq
        WHERE status != 'poisoned'
          AND retry_count < %s
          AND (next_retry_at IS NULL OR next_retry_at <= NOW())
        ORDER BY id ASC
        LIMIT %s
    """

    conn = None
    try:
        conn = _get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (_DLQ_MAX_RETRIES, limit))
        rows = cursor.fetchall()
        cursor.close()
        return rows or []
    except Exception:
        # [Q-B7 修复] logger.exception 自动带堆栈
        logger.exception('[dlq_retry] 查询失败')
        return []
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _try_retry_one(record: dict) -> bool:
    """尝试重试单条记录

    Args:
        record: dlq 表记录

    Returns:
        bool: True=重试成功并删除, False=失败需要继续重试
    """
    record_id = record.get('id')
    payload = record.get('payload')
    retry_count = record.get('retry_count', 0)

    if not payload:
        logger.warning(f'[dlq_retry] 记录 {record_id} payload 为空，跳过')
        return False

    # 尝试重新发送（payload 已经是 JSON 字符串）
    success = _resend_message(payload)

    if success:
        # 成功：删除记录
        _delete_dlq_record(record_id)
        logger.info(
            f'[dlq_retry] ✅ 重试成功 id={record_id} '
            f'prev_retries={retry_count}'
        )
        return True

    # 失败：计算下次重试时间（指数退避）
    next_retry_at = _calc_next_retry(retry_count + 1)
    _update_dlq_retry_count(record_id, retry_count + 1, next_retry_at)

    # [Q-B7 修复] logger.exception 在无异常时不调用
    # 这里失败但不抛异常，用 logger.warning 记录
    logger.warning(
        f'[dlq_retry] ❌ 重试失败 id={record_id} '
        f'next_retry_count={retry_count + 1} next_retry_at={next_retry_at}'
    )
    return False


def _resend_message(payload) -> bool:
    """重新发送消息

    Args:
        payload: JSON 字符串或 dict

    Returns:
        bool: True=发送成功, False=发送失败
    """
    # 解析 payload（如果是字符串）
    if isinstance(payload, (str, bytes)):
        try:
            import json as _json
            payload = _json.loads(payload)
        except Exception:
            logger.warning(f'[dlq_retry] payload 解析失败: {payload[:100] if isinstance(payload, (str, bytes)) else payload}')
            return False

    # 实际发送逻辑（从 dlq 重新入队到消息队列或重发 HTTP）
    # 这里由业务方注入具体的发送函数
    sender = _get_message_sender()
    if not sender:
        logger.warning('[dlq_retry] 无可用 message sender，跳过发送')
        return False

    try:
        return bool(sender(payload))
    except Exception:
        logger.exception('[dlq_retry] 消息发送异常')
        return False


# 消息发送函数注入点（避免循环依赖）
_message_sender = None


def register_message_sender(func):
    """注册消息发送函数

    用法:
        from dispatch_center._dlq_retry import register_message_sender
        def my_sender(payload):
            return call_wechat_api(payload)
        register_message_sender(my_sender)
    """
    global _message_sender
    _message_sender = func
    logger.info(f'[dlq_retry] 已注册 message sender: {func.__name__}')


def _get_message_sender():
    """获取消息发送函数"""
    return _message_sender


def _calc_next_retry(retry_count: int) -> int:
    """计算下次重试时间（指数退避）

    Args:
        retry_count: 即将进行的重试次数

    Returns:
        int: Unix timestamp
    """
    delay = _DLQ_BACKOFF_BASE ** retry_count  # 1, 2, 4, 8, 16, 32...
    return int(time.time()) + delay


def _delete_dlq_record(record_id) -> None:
    """删除 dlq 记录（重试成功）"""
    try:
        from ._db import _get_mysql_connection
    except ImportError:
        return

    conn = None
    try:
        conn = _get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dlq WHERE id=%s", (record_id,))
        conn.commit()
        cursor.close()
    except Exception:
        # [Q-B7 修复] logger.exception
        logger.exception(f'[dlq_retry] 删除记录失败 id={record_id}')
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _update_dlq_retry_count(record_id, retry_count: int, next_retry_at: int) -> None:
    """更新 dlq 记录的重试次数和下次重试时间"""
    try:
        from ._db import _get_mysql_connection
    except ImportError:
        return

    from datetime import datetime

    conn = None
    try:
        conn = _get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE dlq SET retry_count=%s, next_retry_at=%s, updated_at=NOW() WHERE id=%s",
            (retry_count, datetime.fromtimestamp(next_retry_at), record_id)
        )
        conn.commit()
        cursor.close()
    except Exception:
        # [Q-B7 修复] logger.exception
        logger.exception(f'[dlq_retry] 更新重试次数失败 id={record_id}')
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _mark_as_poison(record_id) -> None:
    """标记记录为 poison message（超过最大重试次数）"""
    try:
        from ._db import _get_mysql_connection
    except ImportError:
        return

    conn = None
    try:
        conn = _get_mysql_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE dlq SET status='poisoned', updated_at=NOW() WHERE id=%s",
            (record_id,)
        )
        conn.commit()
        cursor.close()
        # 严重告警
        logger.critical(
            f'[dlq_retry] ☠️ 记录已超过最大重试 {_DLQ_MAX_RETRIES} 次, 标记为 poison, '
            f'id={record_id}'
        )
    except Exception:
        # [Q-B7 修复] logger.exception
        logger.exception(f'[dlq_retry] poison 标记失败 id={record_id}')
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


__all__ = [
    'start_dlq_retry_worker',
    'stop_dlq_retry_worker',
    'get_dlq_stats',
    'register_message_sender',
]
