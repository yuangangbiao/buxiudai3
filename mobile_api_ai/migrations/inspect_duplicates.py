# -*- coding: utf-8 -*-
"""Inspect duplicate data details"""
import sys
import io
import os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# Load .env - go up two levels: migrations/ -> mobile_api_ai/ -> project root
env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
if not os.path.exists(env_file):
    env_file = os.path.join(os.path.dirname(__file__), '..', 'mobile_api_ai', '.env')
if not os.path.exists(env_file):
    env_file = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/.env'
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()
    print(f'[OK] Loaded env from: {env_file}', flush=True)
else:
    print(f'[WARN] .env not found', flush=True)

import pymysql
conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'),
    port=int(os.environ.get('MYSQL_PORT', 3306)),
    user=os.environ.get('MYSQL_USER', 'root'),
    password=os.environ.get('MYSQL_PASSWORD', ''),
    database=os.environ.get('CONTAINER_MYSQL_DATABASE', 'container_center'),
    charset='utf8mb4'
)
cur = conn.cursor()

print('=' * 70, flush=True)
print('Process_sub_steps Duplicate Data Inspection', flush=True)
print('=' * 70, flush=True)

# Total rows
cur.execute("SELECT COUNT(*) FROM process_sub_steps")
total = cur.fetchone()[0]
print(f'Total rows in process_sub_steps: {total}', flush=True)

# Active rows
cur.execute("SELECT COUNT(*) FROM process_sub_steps WHERE status IN ('pending', 'in_progress', 'distributed')")
active = cur.fetchone()[0]
print(f'Active rows (pending/in_progress/distributed): {active}', flush=True)

# Group by status
cur.execute("SELECT status, COUNT(*) FROM process_sub_steps GROUP BY status")
print(f'\nStatus distribution:', flush=True)
for status, count in cur.fetchall():
    print(f'  {status}: {count}', flush=True)

# Top duplicated order_no+step_name
cur.execute("""
SELECT order_no, step_name, status, COUNT(*) as cnt
FROM process_sub_steps
WHERE status IN ('pending', 'in_progress', 'distributed')
GROUP BY order_no, step_name, status
HAVING cnt > 1
ORDER BY cnt DESC LIMIT 10
""")
print(f'\nTop 10 duplicated (order_no, step_name, status):', flush=True)
for order_no, step_name, status, cnt in cur.fetchall():
    print(f'  {order_no} / {step_name} / {status}: {cnt} rows', flush=True)

# Total duplicate groups
cur.execute("""
SELECT COUNT(DISTINCT order_no, step_name, status) FROM (
    SELECT order_no, step_name, status
    FROM process_sub_steps
    WHERE status IN ('pending', 'in_progress', 'distributed')
    GROUP BY order_no, step_name, status
    HAVING COUNT(*) > 1
) t
""")
dup_groups = cur.fetchone()[0]
print(f'\nTotal duplicate groups: {dup_groups}', flush=True)

# Affected orders
cur.execute("""
SELECT COUNT(DISTINCT order_no) FROM process_sub_steps
WHERE status IN ('pending', 'in_progress', 'distributed')
GROUP BY order_no, step_name, status
HAVING COUNT(*) > 1
""")
# This is complex; just count orders with any active sub_step
cur.execute("""
SELECT COUNT(DISTINCT order_no) FROM process_sub_steps
WHERE status IN ('pending', 'in_progress', 'distributed')
""")
active_orders = cur.fetchone()[0]
print(f'Total orders with active sub_steps: {active_orders}', flush=True)

conn.close()
print('\n[Done]', flush=True)