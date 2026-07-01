import json, os, sys
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime, timedelta

sys.stdout = open(sys.stdout.fileno(), mode='w', buffering=1, encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cache_file = os.path.join(PROJECT_ROOT, 'dispatch_center_data.json')
with open(cache_file, 'r', encoding='utf-8') as f:
    dc = json.load(f)

ORDER_NO = 'WO-202605005'
lead_time = 0
for p in dc.get('processes', []):
    if p.get('order_no') == ORDER_NO:
        print(f'=== DC 状态 ===')
        print(f'  current_step: {p["current_step"]}')
        print(f'  status: {p["status"]}')
        lead_time = p.get('lead_time', 0)
        print(f'  lead_time: {lead_time}')
        break

MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'steel_belt')
if not MYSQL_PASSWORD:
    print('❌ 错误: 未设置 MYSQL_PASSWORD 环境变量')
    sys.exit(1)
conn = pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DATABASE, charset='utf8mb4', cursorclass=DictCursor)
c = conn.cursor()

c.execute("SELECT id, order_no, status, plan_start, plan_end, remark FROM production_orders WHERE order_no=%s", (ORDER_NO,))
po = c.fetchone()
c.execute("SELECT id, order_no, status FROM orders WHERE order_no=%s", (ORDER_NO,))
o = c.fetchone()

print(f'\n=== MySQL production_orders ===')
print(f'  status: {po["status"]}' if po else '  (none)')
if po: print(f'  plan_start: {po["plan_start"]}  plan_end: {po["plan_end"]}')
print(f'\n=== MySQL orders ===')
print(f'  status: {o["status"]}' if o else '  (none)')

if po and lead_time and lead_time > 0:
    plan_start = datetime.now().strftime('%Y-%m-%d')
    plan_end = (datetime.now() + timedelta(days=int(lead_time))).strftime('%Y-%m-%d')
    if po['status'] == '待发布':
        c.execute("UPDATE production_orders SET status=%s, plan_start=%s, plan_end=%s, updated_at=NOW() WHERE id=%s",
                  ('生产中', plan_start, plan_end, po['id']))
        conn.commit()
        print(f'\n✅ production_orders: 待发布 → 生产中, plan={plan_start}~{plan_end}')
    else:
        print(f'\n⏭️ production_orders 已是 {po["status"]}, 不覆盖')
    if o and o['status'] == '待发布':
        c.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s", ('已排产', o['id']))
        conn.commit()
        print(f'✅ orders: 待发布 → 已排产')
else:
    print(f'\n⏭️ 无需同步 (lead_time={lead_time})')

conn.close()
print('✅ MySQL 同步完成')
