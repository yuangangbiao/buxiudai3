"""[v2.1 2026-06-21] 桌面端缓存失效客户端(轻量级)

背景: 桌面端直接操作 MySQL steel_belt, 不调用容器中心 API
       → 容器中心 process_records 不知道
       → 调度中心缓存 process_tasks 不会清理

方案: 桌面端删除/归档后, 通过本模块直接 HTTP 调用调度中心清理缓存
     (绕开容器中心, 因为容器中心也没这个数据)

调用: emit_invalidate(order_no, source) - 一行代码接入
"""
import os
import time
import json
import uuid
import logging
import threading
import queue
from typing import Optional

logger = logging.getLogger(__name__)

# ── 配置 ──
DISPATCH_CENTER_URL = os.environ.get(
    'DISPATCH_CENTER_URL', 'http://127.0.0.1:5003'
)
API_KEY = os.environ.get('API_KEY', '')

# ── 异步队列(避免阻塞主线程) ──
_invalidation_queue: "queue.Queue" = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()
_heartbeat = {
    'events': 0,
    'success': 0,
    'failed': 0,
    'last_tick': 0,
}


def _send_once(order_no: str, source: str, record_id: str = '',
               event_id: str = '', max_retry: int = 5) -> bool:
    """同步发送一次失效事件(带重试)

    Returns:
        bool: True=成功, False=失败
    """
    import requests

    url = f'{DISPATCH_CENTER_URL}/api/dispatch-center/cache/invalidate'
    payload = {
        'event_id': event_id or str(uuid.uuid4()),
        'order_no': order_no,
        'source': source,
        'record_id': record_id,
        'timestamp': time.time(),
    }

    headers = {'Content-Type': 'application/json'}
    if API_KEY:
        headers['X-API-Key'] = API_KEY

    last_err = None
    for attempt in range(max_retry):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=3)
            if resp.status_code == 200:
                result = resp.json()
                if result.get('code') == 0:
                    return True
                last_err = f'HTTP 200 but code={result.get("code")}: {result.get("message", "")}'
            else:
                last_err = f'HTTP {resp.status_code}'
        except requests.ConnectionError as e:
            last_err = f'ConnectionError: {e}'
        except Exception as e:
            last_err = f'{type(e).__name__}: {e}'

        if attempt < max_retry - 1:
            time.sleep(2 ** attempt)  # 1s, 2s, 4s, 8s, 16s

    logger.warning(f'[desktop-invalidate] 彻底失败: {order_no} ({source}): {last_err}')
    return False


def _worker_loop():
    """后台 worker 循环"""
    consecutive_errors = 0
    while True:
        try:
            event = _invalidation_queue.get(timeout=5)
            _heartbeat['last_tick'] = time.time()
            ok = _send_once(
                order_no=event['order_no'],
                source=event['source'],
                record_id=event.get('record_id', ''),
                event_id=event['event_id'],
            )
            _heartbeat['events'] += 1
            if ok:
                _heartbeat['success'] += 1
                consecutive_errors = 0
            else:
                _heartbeat['failed'] += 1
                consecutive_errors += 1
        except queue.Empty:
            continue
        except Exception as e:
            consecutive_errors += 1
            logger.error(f'[desktop-invalidate] worker 异常: {e}')
        if consecutive_errors >= 10:
            logger.critical('[desktop-invalidate] 连续10次异常, 告警')
            consecutive_errors = 0  # 重置避免持续告警


def _ensure_worker():
    """确保后台 worker 已启动"""
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True
        t = threading.Thread(
            target=_worker_loop,
            name='DesktopInvalidationWorker',
            daemon=True,
        )
        t.start()
        logger.info(
            f'[desktop-invalidate] worker 已启动, '
            f'dispatch_url={DISPATCH_CENTER_URL}'
        )


def emit_invalidate(order_no: str, source: str, record_id: str = '',
                    sync: bool = False) -> bool:
    """发出失效事件(默认异步,不阻塞调用方)

    Args:
        order_no: 订单号
        source: 触发源标识
            - order_delete: 订单删除
            - order_archive: 订单归档
            - order_unarchive: 取消归档
            - process_delete: 工序删除
            - process_soft_delete: 工序软删
        record_id: 相关记录 ID(可选)
        sync: True=同步发送(阻塞), False=异步(默认)

    Returns:
        bool: True=已成功发送/入队, False=失败
    """
    if not order_no:
        return False

    if sync:
        return _send_once(order_no, source, record_id)

    event = {
        'event_id': str(uuid.uuid4()),
        'order_no': order_no,
        'source': source,
        'record_id': record_id,
        'timestamp': time.time(),
    }
    try:
        _invalidation_queue.put_nowait(event)
        _ensure_worker()
        return True
    except queue.Full:
        logger.error(f'[desktop-invalidate] 队列已满, 事件丢失: {order_no}')
        return False


def get_heartbeat() -> dict:
    """获取 worker 心跳状态(供调试)"""
    return dict(_heartbeat)


# 模块导入时自动启动 worker
_ensure_worker()
