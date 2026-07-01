# -*- coding: utf-8 -*-
"""
[E2 修复 2026-06-13] Outbox 兜底 worker

用途：8008 mirror 失败时写 outbox 表，由 5002 启动的 outbox worker 消费
"""
import os, sys as _sys
_MAI = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_MAI)
if _MAI in _sys.path:
    _sys.path.remove(_MAI)
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)
if _MAI not in _sys.path:
    _sys.path.append(_MAI)

import json
import time
import logging
import threading
from typing import Optional
import pymysql

logger = logging.getLogger(__name__)

# [K19 修复 2026-06-14] 与 5002 容器中心使用相同的默认密钥
_MIRROR_SECRET = os.getenv('MIRROR_SHARED_SECRET', 'yuan-mirror-2026')

# [K19 修复 2026-06-14] 全局线程引用，保证 start 幂等
_outbox_thread: Optional[threading.Thread] = None

# ── dispatch_center 推送 ──

def _dispatch_to_center(event_id: str, action: str, payload: dict,
                        cc_url: str, headers: dict) -> bool:
    """推送到 dispatch_center /api/sync/outbox-event

    Returns:
        True=成功，False=失败
    """
    try:
        import requests as _req
        resp = _req.post(
            f'{cc_url}/api/sync/outbox-event',
            headers=headers,
            json={
                'event_id': event_id,
                'action': action,
                'payload': payload,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return True
        logger.warning('[outbox→dc] HTTP %d: %s', resp.status_code, resp.text[:200])
        return False
    except Exception as e:
        logger.warning('[outbox→dc] 请求失败: %s', e)
        return False


def _trigger_dead_letter_alert(dead_rows: list):
    """[F8 修复 2026-06-13] 触发 outbox 死信告警

    Args:
        dead_rows: 死信记录列表
    """
    try:
        count = len(dead_rows)
        # 1. 写 outbox_dead_letter 告警表
        conn = _get_mysql_conn()
        try:
            with conn.cursor() as c:
                c.execute("""
                    CREATE TABLE IF NOT EXISTS outbox_dead_letter_alert (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        dead_count INT,
                        sample_trace_id VARCHAR(64),
                        sample_error TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                c.execute("""
                    INSERT INTO outbox_dead_letter_alert (dead_count, sample_trace_id, sample_error)
                    VALUES (%s, %s, %s)
                """, (
                    count,
                    dead_rows[0].get('trace_id', '')[:64] if dead_rows else '',
                    str(dead_rows[0].get('last_error', ''))[:500] if dead_rows else '',
                ))
            conn.commit()
        finally:
            conn.close()

        # 2. 调 5003 微信通知
        try:
            import requests as _req
            _req.post(
                f'{os.getenv("DISPATCH_CENTER_URL", "http://127.0.0.1:5003")}/api/notify/wechat',
                json={
                    'message': f'⚠️ Outbox 死信告警\n数量: {count} 条/小时\n示例: trace_id={dead_rows[0].get("trace_id", "")[:16] if dead_rows else "N/A"}',
                    'level': 'error',
                },
                timeout=2,
            )
        except Exception:
            pass

        logger.error(f'[OUTBOX ALERT] 死信 {count} 条/小时, 告警已触发')
    except Exception as e:
        logger.error(f'[OUTBOX] 死信告警触发失败: {e}')


def _write_mirror_outbox(payload: dict):
    """[E2 修复] 写 mirror 失败的消息到 outbox 表

    Args:
        payload: mirror 请求体
    """
    try:
        from core.config import CONTAINER_MYSQL_CFG
        from utils.trace import get_trace_id
        from core.db_compat import get_conn
        conn = get_conn()
        try:
            with conn.cursor() as c:
                # [F1 修复 2026-06-13] 用真实 trace_id，不用 uuid
                _trace_id = get_trace_id() or payload.get('uuid', 'unknown')
                c.execute("""
                    INSERT INTO sync_outbox 
                    (trace_id, action, target_db, payload, status, retry_count, max_retries, created_at)
                    VALUES (%s, %s, %s, %s, 'pending', 0, 5, NOW())
                """, (
                    _trace_id,
                    'process_sub_step_mirror',
                    'container_center',
                    json.dumps(payload, ensure_ascii=False),
                ))
            conn.commit()
            logger.info(f'[OUTBOX] 写入 mirror 失败重试: trace_id={_trace_id[:16]}..., uuid={payload.get("uuid", "")[:8]}')
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f'[OUTBOX] 写 outbox 失败: {e}')


def _get_mysql_conn():
    """[T11 2026-06-14] 走 shim 连接池"""
    from core.db_compat import get_conn
    return get_conn()


def _process_outbox_once():
    """处理一批 outbox 消息（每 30s 调用一次）

    [H6 修复 2026-06-13] 多实例部署时使用分布式锁
    防止多实例同时消费 outbox 表导致重复调用 /mirror

    支持两种 outbox 表：
    - container_center.sync_outbox：legacy 路径（process_sub_step_mirror → 推容器中心）
    - steel_belt.sync_outbox：       新路径（orders/process_records → 推调度中心）
    """
    total_processed = 0
    # 1. 处理 legacy container_center outbox
    total_processed += _process_container_outbox()
    # 2. 处理 steel_belt outbox（新路径 → 推调度中心）
    total_processed += _process_steelbelt_outbox()
    return total_processed


def _process_container_outbox():
    """处理 container_center.sync_outbox（legacy process_sub_step_mirror）"""
    try:
        from utils.trace import get_trace_id, traced_request
        conn = _get_mysql_conn()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as c:
                # 死信告警
                c.execute("""
                    SELECT id, trace_id, last_error, created_at
                    FROM sync_outbox
                    WHERE status = 'dead' AND created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                      AND action = 'process_sub_step_mirror'
                """)
                dead_rows = c.fetchall()
                if dead_rows:
                    _trigger_dead_letter_alert(dead_rows)

                # 分布式锁：查 pending 记录
                try:
                    c.execute("""
                        SELECT id, trace_id, action, target_db, payload, retry_count, max_retries
                        FROM sync_outbox
                        WHERE status = 'pending' AND action = 'process_sub_step_mirror'
                        ORDER BY created_at ASC
                        LIMIT 50
                        FOR UPDATE SKIP LOCKED
                    """)
                except pymysql.OperationalError:
                    logger.warning('[H6] MySQL 不支持 SKIP LOCKED')
                    c.execute("""
                        SELECT id, trace_id, action, target_db, payload, retry_count, max_retries
                        FROM sync_outbox
                        WHERE status = 'pending' AND action = 'process_sub_step_mirror'
                        ORDER BY created_at ASC
                        LIMIT 50
                    """)
                rows = c.fetchall()
                if not rows:
                    return 0

                processed = 0
                cc_url = os.getenv('CONTAINER_CENTER_URL', 'http://127.0.0.1:5002')
                for row in rows:
                    try:
                        payload = json.loads(row['payload']) if isinstance(row['payload'], str) else row['payload']
                        resp = traced_request('POST', f'{cc_url}/api/process_sub_steps/mirror',
                                             headers={'X-Mirror-Secret': _MIRROR_SECRET},
                                             json=payload, timeout=3)
                        if resp.status_code == 200:
                            c.execute("UPDATE sync_outbox SET status='processed', processed_at=NOW() WHERE id=%s", (row['id'],))
                            conn.commit()
                            processed += 1
                        else:
                            new_retry = row['retry_count'] + 1
                            status = 'dead' if new_retry >= row['max_retries'] else 'pending'
                            c.execute("UPDATE sync_outbox SET status=%s, retry_count=%s, last_error=%s WHERE id=%s",
                                      (status, new_retry, f'HTTP {resp.status_code}', row['id']))
                            conn.commit()
                    except Exception as e:
                        new_retry = row['retry_count'] + 1
                        status = 'dead' if new_retry >= row['max_retries'] else 'pending'
                        c.execute("UPDATE sync_outbox SET status=%s, retry_count=%s, last_error=%s WHERE id=%s",
                                  (status, new_retry, str(e)[:500], row['id']))
                        conn.commit()
                if processed > 0:
                    logger.info(f'[OUTBOX legacy] 处理 {processed}/{len(rows)} 条')
                return processed
        finally:
            conn.close()
    except Exception as e:
        logger.warning('[OUTBOX legacy] 处理失败: %s', e)
        return 0


def _process_steelbelt_outbox():
    """处理 steel_belt.sync_outbox（新路径 → 推调度中心）

    支持 action：orders.create / orders.update / process_records.update / quality_records.create
    """
    try:
        from core.db_compat import get_conn as _get_sb_conn
        conn = _get_sb_conn(**{
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': 'steel_belt',
            'charset': 'utf8mb4',
        })
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as c:
                c.execute("""
                    CREATE TABLE IF NOT EXISTS sync_outbox (
                        id              INT PRIMARY KEY AUTO_INCREMENT,
                        event_id       VARCHAR(64)  NOT NULL DEFAULT '',
                        action         VARCHAR(64)  NOT NULL COMMENT '事件类型: {table}.{op}',
                        target_db      VARCHAR(32)  NOT NULL DEFAULT 'dispatch_center',
                        record_id      VARCHAR(64)  NOT NULL DEFAULT '',
                        payload        JSON         NOT NULL,
                        status         VARCHAR(16)  NOT NULL DEFAULT 'pending',
                        retry_count    INT          NOT NULL DEFAULT 0,
                        max_retries    INT          NOT NULL DEFAULT 5,
                        last_error     TEXT,
                        created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        processed_at   DATETIME,
                        INDEX idx_status_action (status, action),
                        INDEX idx_event_id (event_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                conn.commit()

                c.execute("""
                    SELECT id, event_id, action, record_id, payload, retry_count, max_retries
                    FROM sync_outbox
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT 50
                """)
                rows = c.fetchall()
                if not rows:
                    return 0

                processed = 0
                dc_url = os.getenv('DISPATCH_CENTER_URL', 'http://127.0.0.1:5003')
                dc_headers = {'Content-Type': 'application/json'}
                _key = os.getenv('CONTAINER_CENTER_API_KEY', '') or os.getenv('API_KEY', '')
                if _key:
                    dc_headers['X-API-Key'] = _key

                for row in rows:
                    try:
                        payload = json.loads(row['payload']) if isinstance(row['payload'], str) else row['payload']
                        ok = _dispatch_to_center(
                            event_id=row.get('event_id', f"{row['action']}:{row['record_id']}"),
                            action=row['action'],
                            payload=payload,
                            cc_url=dc_url,
                            headers=dc_headers,
                        )
                        if ok:
                            c.execute("UPDATE sync_outbox SET status='processed', processed_at=NOW() WHERE id=%s", (row['id'],))
                            conn.commit()
                            processed += 1
                        else:
                            new_retry = row['retry_count'] + 1
                            status = 'dead' if new_retry >= row['max_retries'] else 'pending'
                            c.execute("UPDATE sync_outbox SET status=%s, retry_count=%s, last_error='HTTP push failed' WHERE id=%s",
                                      (status, new_retry, row['id']))
                            conn.commit()
                    except Exception as e:
                        new_retry = row['retry_count'] + 1
                        status = 'dead' if new_retry >= row['max_retries'] else 'pending'
                        c.execute("UPDATE sync_outbox SET status=%s, retry_count=%s, last_error=%s WHERE id=%s",
                                  (status, new_retry, str(e)[:500], row['id']))
                        conn.commit()
                if processed > 0:
                    logger.info('[SB outbox] 处理 %d/%d 条', processed, len(rows))
                return processed
        finally:
            conn.close()
    except Exception as e:
        logger.warning('[SB outbox] 处理失败: %s', e)
        return 0


# ============= 后台线程 =============
_outbox_running = threading.Event()
_outbox_stop = threading.Event()


def start_outbox_worker(interval_sec: int = 30):
    """启动 outbox 后台 worker

    [E2 修复 2026-06-13] 定期消费 sync_outbox 表
    [P1 集成 thread_lifecycle 2026-06-13] 支持优雅停止
    [K17 修复 2026-06-14] 幂等 - 多次启动不创建重复线程
    """
    # [K17 修复 2026-06-14] 幂等性保证
    global _outbox_thread
    if _outbox_thread is not None and _outbox_thread.is_alive():
        logger.info('[OUTBOX Worker] 已在运行，跳过启动')
        return _outbox_thread
    def _worker():
        # [Q9 修复 2026-06-13] 包裹 try/except，防止初始异常导致线程静默死亡
        try:
            logger.info(f'[OUTBOX Worker] 启动，处理间隔 {interval_sec}s')
            # 启动时立即处理一次
            _process_outbox_once()
        except Exception as e:
            logger.error(f'[OUTBOX Worker] 初始处理失败: {e}', exc_info=True)
            return  # 线程退出（避免静默死掉）
        while not _outbox_stop.is_set():
            for _ in range(int(interval_sec * 2)):
                if _outbox_stop.is_set():
                    break
                time.sleep(0.5)
            if not _outbox_stop.is_set():
                try:
                    _process_outbox_once()
                except Exception as e:
                    logger.warning(f'[OUTBOX Worker] 异常: {e}')
        logger.info('[OUTBOX Worker] 收到停止信号，退出')

    try:
        from thread_lifecycle import create_daemon_thread
        _outbox_thread = create_daemon_thread(name='outbox-worker', target=_worker)
    except ImportError:
        _outbox_thread = threading.Thread(target=_worker, daemon=True, name='outbox-worker')
        _outbox_thread.start()
    logger.info('[OUTBOX Worker] 线程已启动')
    return _outbox_thread


def stop_outbox_worker():
    """停止 outbox worker"""
    _outbox_stop.set()


def manual_process_once() -> int:
    """手动处理一次（用于测试或运维）"""
    return _process_outbox_once()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    n = manual_process_once()
    print(f'处理完成: {n} 条')
