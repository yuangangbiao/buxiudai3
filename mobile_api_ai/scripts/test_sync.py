import urllib.request, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

url = 'http://127.0.0.1:5003/api/dispatch-center/processes?page=1&page_size=50'
with urllib.request.urlopen(url) as r:
    data = json.loads(r.read())
print('=== dispatch_center 娴佺▼鍒楄〃 ===')
for p in data.get('data', []):
    print(f"  {p['order_no']}: step={p['current_step']} status={p['status']} lead_time={p.get('lead_time','N/A')}")

print()
print('=== MySQL 鍚屾楠岃瘉 ===')
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime, timedelta

MYSQL_CFG = {
    'host': os.environ.get('MYSQL_HOST', ''),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4',
}
conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor)
c = conn.cursor()

for order_no in ['WO-202605004', 'WO-202605005']:
    c.execute("SELECT id, order_no, status, plan_start, plan_end, remark FROM production_orders WHERE order_no=%s", (order_no,))
    po = c.fetchone()
    c.execute("SELECT id, order_no, status FROM orders WHERE order_no=%s", (order_no,))
    o = c.fetchone()
    print(f"\n{order_no}:")
    print(f"  production_orders: status={po['status'] if po else 'NOT FOUND'}, plan={po['plan_start']}~{po['plan_end'] if po else 'N/A'}")
    print(f"  orders:           status={o['status'] if o else 'NOT FOUND'}")

conn.close()
print()
print('=== 鎻愮ず锛氫綘鐜板湪鍙互鍦ㄩ〉闈笂鎿嶄綔鎺ㄨ繘 WO-202605005锛?)
print('   姣忔鎿嶄綔鍚?dispatch_center 浼氳嚜鍔ㄥ悓姝ュ埌 MySQL ===')
