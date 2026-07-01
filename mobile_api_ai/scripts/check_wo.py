# -*- coding: utf-8 -*-
import sqlite3, os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mobile_api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(mobile_api_dir, 'wechat_container.db')

print(f'数据库: {db_path}')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

target = 'wo2026050009'
print(f'\n=== 在 process_records 中搜索 {target} ===')
cursor.execute("SELECT id, order_no, quantity FROM process_records WHERE order_no LIKE ?", (f'%{target}%',))
rows = cursor.fetchall()
print(f'  找到 {len(rows)} 条')
for r in rows:
    print(f'  id={r["id"]} order_no={r["order_no"]} qty={r["quantity"]}')

print(f'\n=== 在 process_sub_steps 中搜索 {target} ===')
cursor.execute("SELECT id, process_id, order_no, step_name, quantity, operator, created_at FROM process_sub_steps WHERE order_no LIKE ?", (f'%{target}%',))
rows = cursor.fetchall()
print(f'  找到 {len(rows)} 条')
for r in rows:
    pid = str(r['process_id'])
    print(f'  id={r["id"][:12]}.. pid={pid[:12]}.. order={r["order_no"]} step={r["step_name"]} qty={r["quantity"]} op={r["operator"]} created={r["created_at"]}')

# 如果没找到，显示全部
cursor.execute("SELECT COUNT(*) FROM process_sub_steps WHERE order_no LIKE ?", (f'%{target}%',))
found_count = cursor.fetchone()[0]
if found_count == 0:
    print(f'\n=== 未找到 {target}，显示全部 process_records order_no ===')
    cursor.execute("SELECT id, order_no, quantity FROM process_records ORDER BY created_at DESC LIMIT 20")
    for r in cursor.fetchall():
        print(f'  id={r["id"]} order_no={r["order_no"]} qty={r["quantity"]}')
    
    print(f'\n=== 全部 process_sub_steps order_no（最近20条） ===')
    cursor.execute("SELECT order_no, step_name, quantity, created_at FROM process_sub_steps ORDER BY created_at DESC LIMIT 20")
    for r in cursor.fetchall():
        print(f'  order_no={r["order_no"]} step={r["step_name"]} qty={r["quantity"]} created={r["created_at"]}')

conn.close()
