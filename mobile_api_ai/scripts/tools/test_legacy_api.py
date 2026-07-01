"""测试 legacy_routes 的数据库查询"""
import sqlite3, os

db_path = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. dashboard 数据
cur.execute('SELECT * FROM orders ORDER BY id')
orders = [dict(r) for r in cur.fetchall()]
total = len(orders)
pending = sum(1 for o in orders if o.get('status') == 'pending')
processing = sum(1 for o in orders if o.get('status') == 'processing')
completed = sum(1 for o in orders if o.get('status') == 'completed')
print(f'=== dashboard ===')
print(f'  totalOrders: {total}')
print(f'  pendingOrders: {pending}')
print(f'  processingOrders: {processing}')
print(f'  completedOrders: {completed}')
urgent = [o for o in orders if o.get('priority') == 'urgent']
print(f'  urgentOrders count: {len(urgent)}')
for o in urgent:
    print(f'    {o["order_id"]} - {o["name"]}')

# 2. sub_steps
cur.execute('SELECT * FROM sub_steps ORDER BY created_at DESC')
sub_steps = [dict(r) for r in cur.fetchall()]
today = '2026-05-18'
today_reports = sum(1 for s in sub_steps if s.get('created_at', '').startswith(today))
print(f'  todayReports: {today_reports}')
print(f'  recentRecords count: {len(sub_steps[:10])}')
for s in sub_steps[:3]:
    print(f'    order_no={s["order_no"]}, step={s["step_name"]}, qty={s["quantity"]}, op={s["operator"]}')

# 3. workers
cur.execute('SELECT username, name, role, created_at FROM workers ORDER BY id')
workers = [dict(r) for r in cur.fetchall()]
print(f'\n=== workers ({len(workers)}) ===')
for w in workers:
    print(f'  {w["name"]} ({w["username"]}) - {w["role"]}')

# 4. production-orders
print(f'\n=== production-orders ({len(orders)}) ===')
for o in orders:
    print(f'  {o["order_id"]}: {o["name"]} ({o["status"]})')

conn.close()
