# -*- coding: utf-8 -*-
"""
同步桌面端发布的 task_published 到 process_task
将 container_center.process_report 中 event_type='task_published' 的记录
转换为 data_packages.process_task
"""
import os, sys, json, uuid, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pymysql

DB = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "88888888"),
    "charset": "utf8mb4",
    "autocommit": False,
}

def log(msg, level="INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "  ", "OK": "✓", "WARN": "⚠", "ERR": "✗"}
    print(f"  [{ts}] {icons.get(level, ' ')} {msg}", flush=True)

def get_conn(db):
    c = pymysql.connect(database=db, **DB)
    c.cursor().execute("SET NAMES utf8mb4")
    return c

def main():
    print("=" * 60)
    print("  SQL#7: 同步 task_published → process_task")
    print("=" * 60)

    conn = get_conn("container_center")
    cur = conn.cursor()

    # 1. 查所有 task_published 记录
    cur.execute("""
        SELECT id, related_order, content
        FROM data_packages
        WHERE data_type='process_report'
          AND JSON_EXTRACT(content, '$.event_type') = 'task_published'
        ORDER BY related_order, created_at
    """)
    published = cur.fetchall()
    log(f"找到 {len(published)} 条 task_published 记录")

    # 2. 查已有 process_task（避免重复）
    cur.execute("""
        SELECT related_order, related_process, content
        FROM data_packages
        WHERE data_type='process_task'
    """)
    existing = {(r[0], r[1]) for r in cur.fetchall()}
    log(f"已有 process_task: {len(existing)} 条")

    # 3. 生成新 process_task
    new_tasks = []
    for row in published:
        pkg_id, order_no, content_str = row
        try:
            content = json.loads(content_str) if isinstance(content_str, str) else content_str
        except:
            content = {}

        process = content.get("process", "")
        quantity = content.get("quantity", 0)
        operator = content.get("operator_id", "") or content.get("operator_name", "")
        event_id = content.get("task_id", pkg_id)
        created_at = content.get("created_at", "")

        if (order_no, process) in existing:
            continue

        task_content = json.dumps({
            "process_name": process,
            "planned_qty": quantity,
            "operator": operator,
            "source": "task_published",
            "source_pkg_id": pkg_id,
            "event_id": event_id,
            "published_at": created_at,
        }, ensure_ascii=False)

        title = f"{order_no} - {process}"
        new_tasks.append((
            f"PKG-{uuid.uuid4().hex[:12].upper()}",
            "process_task",
            title,
            task_content,
            "sync_task_published",
            "pending" if quantity == 0 else "pending",
            operator,
            "",
            order_no,
            process,
            0, 0, 0, "normal",
        ))

    log(f"将插入 {len(new_tasks)} 条新 process_task")

    if not new_tasks:
        log("无需插入", "INFO")
        conn.close()
        return

    conn.autocommit = False
    cur.executemany("""
        INSERT INTO data_packages
            (id, data_type, title, content, source, status,
             target_operator, operator_id, order_no, related_process,
             completed_qty, progress_qty, actual_qty, priority, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """, new_tasks)

    log(f"插入 {cur.rowcount} 行", "OK")
    conn.commit()
    conn.close()

    # 4. 验证
    conn2 = get_conn("container_center")
    cur2 = conn2.cursor()
    cur2.execute("""
        SELECT order_no, related_process, status, content
        FROM data_packages
        WHERE data_type='process_task'
          AND source='sync_task_published'
        ORDER BY order_no
    """)
    rows = cur2.fetchall()
    log(f"验证: sync_task_published 共 {len(rows)} 条")
    for r in rows:
        content = {}
        try: content = json.loads(r[3])
        except: pass
        log(f"  {r[0]} | {r[1]} | qty={content.get('planned_qty')} | op={content.get('operator')}")
    conn2.close()

    print()
    log(f"完成: 新增 {len(new_tasks)} 条 process_task", "OK")

if __name__ == "__main__":
    main()
