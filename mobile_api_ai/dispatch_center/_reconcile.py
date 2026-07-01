"""[v2.1 2026-06-21] 调度中心缓存对账 worker

背景: 容器中心 → 调度中心的失效事件可能因为网络中断、worker 异常等原因丢失
      导致调度中心缓存的 process_tasks 存在孤立数据
方案: 定期对比容器中心 process_records 和调度中心缓存,清理孤立数据

调用: dispatch_center 启动时调用 start_reconcile_worker()
"""
import os
import time
import threading
import logging
from typing import Set

logger = logging.getLogger(__name__)

# ── 配置 ──
_RECONCILE_INTERVAL = int(os.environ.get('RECONCILE_INTERVAL', '600'))  # 10 分钟
_RECONCILE_BATCH_SIZE = 2000
_RECONCILE_WORKER_STARTED = False
_RECONCILE_WORKER_LOCK = threading.Lock()
_RECONCILE_LAST_RUN = {'ts': 0, 'orphans': 0}


def start_reconcile_worker() -> bool:
    """启动对账 worker(幂等,只能启动一次)

    Returns:
        bool: True=本次启动了, False=之前已启动
    """
    global _RECONCILE_WORKER_STARTED
    with _RECONCILE_WORKER_LOCK:
        if _RECONCILE_WORKER_STARTED:
            return False
        _RECONCILE_WORKER_STARTED = True
    t = threading.Thread(
        target=_reconcile_loop,
        name='ReconcileWorker',
        daemon=True,
    )
    t.start()
    logger.info(f'[reconcile] worker 已启动, interval={_RECONCILE_INTERVAL}s')
    return True


def _reconcile_loop():
    """对账主循环(每 _RECONCILE_INTERVAL 秒一次)"""
    while True:
        time.sleep(_RECONCILE_INTERVAL)
        try:
            _reconcile_once()
        except Exception as e:
            logger.error(f'[reconcile] 对账失败: {e}', exc_info=True)


def _reconcile_once() -> int:
    """单次对账执行

    Returns:
        int: 清理的孤立数据条数
    """
    from ._db import _dispatch_cache

    # 1. 从容器中心获取真实工单
    cc_url = os.environ.get('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')
    api_key = os.environ.get('API_KEY', '')

    headers = {'X-API-Key': api_key} if api_key else {}
    try:
        # [v2.1 修正] 端点: /api/processes (不是 /api/process_records)
        import requests
        resp = requests.get(
            f'{cc_url}/api/processes?limit={_RECONCILE_BATCH_SIZE}',
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning(f'[reconcile] 容器中心返回 {resp.status_code}')
            return 0
        cc_data = resp.json().get('data', [])
        cc_order_nos: Set[str] = {
            item.get('order_no') for item in cc_data
            if isinstance(item, dict) and item.get('order_no')
        }
    except Exception as e:
        logger.warning(f'[reconcile] 获取容器中心工单失败: {e}')
        return 0

    # 2. 从调度中心缓存获取
    cache = _dispatch_cache.get_data()
    cache_tasks = cache.get('process_tasks', [])
    cache_order_nos: Set[str] = {
        t.get('order_no') for t in cache_tasks if t.get('order_no')
    }

    # 3. 找出孤立数据(缓存中有,容器中心没有)
    orphans = cache_order_nos - cc_order_nos
    if not orphans:
        logger.debug(
            f'[reconcile] 无孤立数据, 共 {len(cache_order_nos)} 工单'
        )
        _RECONCILE_LAST_RUN.update({'ts': time.time(), 'orphans': 0})
        return 0

    logger.warning(f'[reconcile] 发现 {len(orphans)} 个孤立工单: {orphans}')

    # 4. 清理(用 list comprehension,避免 in-flight 修改)
    orphan_set = set(orphans)

    def _clean(d):
        d['process_tasks'] = [
            t for t in d.get('process_tasks', [])
            if t.get('order_no') not in orphan_set
        ]
        d['work_orders'] = [
            w for w in d.get('work_orders', [])
            if w.get('order_no') not in orphan_set
        ]

    _dispatch_cache.update_data(_clean)
    _RECONCILE_LAST_RUN.update({'ts': time.time(), 'orphans': len(orphans)})
    logger.info(f'[reconcile] 清理 {len(orphans)} 个孤立工单')
    return len(orphans)


def get_reconcile_status() -> dict:
    """获取对账状态(用于健康检查接口)"""
    return {
        'started': _RECONCILE_WORKER_STARTED,
        'interval': _RECONCILE_INTERVAL,
        'last_run_ts': _RECONCILE_LAST_RUN.get('ts', 0),
        'last_orphans': _RECONCILE_LAST_RUN.get('orphans', 0),
    }


def force_reconcile_once() -> int:
    """强制执行一次对账(供运维/测试手动调用)

    Returns:
        int: 清理的孤立数据条数
    """
    return _reconcile_once()
