# -*- coding: utf-8 -*-
import sqlite3, os, sys

# 强制设置 stdout 编码
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

mobile_api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(mobile_api_dir, 'wechat_container.db')

print('=== 模拟写入测试（无 emoji）===')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
try:
    cursor.execute('BEGIN IMMEDIATE')
    import uuid
    test_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO process_sub_steps (id, process_id, order_no, step_name, batch_no, quantity, qualified_qty, operator, remark, equipment_name, overtime_hours, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (test_id, 'test-pid', 'TEST-ORDER', 'test-step', 'TEST-BATCH', 1.0, 1.0, 'test-operator', 'test-remark', '', 0, '2026-01-01T00:00:00')
    )
    cursor.execute('ROLLBACK')
    print('  直接 SQL INSERT: 成功')
except Exception as e:
    print(f'  直接 SQL INSERT: 失败 - {e}')

print()
print('=== 调查：超计划拦截可能涉及的 process_id ===')
cursor.execute("SELECT DISTINCT process_id FROM process_sub_steps WHERE process_id GLOB '*-*' LIMIT 10")
for r in cursor.fetchall():
    pid = r['process_id']
    cursor.execute("SELECT quantity, order_no FROM process_records WHERE id = ?", (pid,))
    pr = cursor.fetchone()
    if pr:
        order_qty = float(pr['quantity'])
        cursor.execute("SELECT COALESCE(SUM(quantity), 0) FROM process_sub_steps WHERE process_id = ?", (pid,))
        total = float(cursor.fetchone()[0])
        print(f"  pid={pid[:16]}.. order={pr['order_no']} order_qty={order_qty} total_reported={total}")

conn.close()
