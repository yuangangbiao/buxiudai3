# -*- coding: utf-8 -*-
"""持久化重试队列 — sqlite 实现，进程重启后任务不丢"""

import sqlite3
import threading
import time
import json
import logging
import os

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'retry_queue.db')

_lock = threading.Lock()
_worker_thread = None
_worker_running = False


def _get_db():
    """获取 sqlite 连接"""
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS retry_tasks ("
                 "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "task_id TEXT UNIQUE, "
                 "payload TEXT, "
                 "attempt INTEGER DEFAULT 0, "
                 "max_retries INTEGER DEFAULT 3, "
                 "next_retry_at REAL, "
                 "status TEXT DEFAULT 'pending', "
                 "created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.row_factory = sqlite3.Row
    return conn


def enqueue_retry(data: dict, max_retries: int = 3) -> str:
    """入队持久化重试任务"""
    import uuid
    task_id = data.get('task_id') or str(uuid.uuid4())[:8]
    task_id = str(task_id)
    payload = json.dumps(data, ensure_ascii=False, default=str)

    conn = _get_db()
    # upsert: 相同 task_id 更新
    existing = conn.execute("SELECT id FROM retry_tasks WHERE task_id=?", (task_id,)).fetchone()
    if existing:
        conn.execute("UPDATE retry_tasks SET payload=?, attempt=0, next_retry_at=?, status='pending' WHERE id=?",
                     (payload, time.time(), existing[0]))
    else:
        conn.execute("INSERT INTO retry_tasks (task_id, payload, max_retries, next_retry_at) VALUES (?,?,?,?)",
                     (task_id, payload, max_retries, time.time()))
    conn.commit()
    conn.close()
    return task_id


def _process_one(conn, row):
    """处理单个重试任务，返回是否成功"""
    conn.execute("UPDATE retry_tasks SET attempt=attempt+1 WHERE id=?", (row['id'],))

    try:
        data = json.loads(row['payload'])
        from app import app
        with app.test_client() as client:
            resp = client.post(data.get('url', '/api/process_sub_step'),
                               json=data.get('body', {}))
            if resp.status_code == 200:
                conn.execute("DELETE FROM retry_tasks WHERE id=?", (row['id'],))
                return True
    except Exception as e:
        logger.warning(f"[RetryQueue] 重试失败 task={row['task_id']}: {e}")

    if row['attempt'] + 1 >= row['max_retries']:
        conn.execute("UPDATE retry_tasks SET status='dead' WHERE id=?", (row['id'],))
        logger.error(f"[RetryQueue] 死信 task={row['task_id']}")
    return False


def process_retry_queue() -> int:
    """扫描并处理到期的重试任务。返回处理数。"""
    conn = _get_db()
    now = time.time()
    rows = conn.execute(
        "SELECT * FROM retry_tasks WHERE status='pending' AND next_retry_at <= ? ORDER BY id LIMIT 10",
        (now,)).fetchall()
    count = 0
    for row in rows:
        try:
            if _process_one(conn, row):
                count += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return count


def start_retry_worker(interval: int = 5):
    """启动后台重试线程"""
    global _worker_thread, _worker_running
    if _worker_running:
        return
    _worker_running = True

    def _loop():
        while _worker_running:
            try:
                process_retry_queue()
            except Exception:
                pass
            time.sleep(interval)

    _worker_thread = threading.Thread(target=_loop, daemon=True, name='retry-worker')
    _worker_thread.start()
    logger.info("[RetryQueue] 后台重试线程已启动")


def stop_retry_worker():
    global _worker_running
    _worker_running = False
