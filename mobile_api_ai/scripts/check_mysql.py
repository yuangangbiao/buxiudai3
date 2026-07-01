"""妫€鏌?MySQL 杩為€氭€у拰 WO-202605005 褰撳墠鐘舵€?""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('d:/yuan/涓嶉攬閽㈢綉甯﹁窡鍗?.0/mobile_api_ai/.env')

import os, pymysql
from pymysql.cursors import DictCursor

cfg = {
    'host': os.environ.get('MYSQL_HOST', ''),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4',
}

print("=== MySQL 杩炴帴閰嶇疆 ===")
for k, v in cfg.items():
    if k == 'password':
        print(f"  {k}: {'***' if v else '(绌?'}")
    else:
        print(f"  {k}: {v}")

conn = pymysql.connect(**cfg, cursorclass=DictCursor, connect_timeout=3)
c = conn.cursor()

c.execute('SELECT COUNT(*) as cnt FROM production_orders')
cnt = c.fetchone()['cnt']
print(f"\n=== production_orders 鍏?{cnt} 鏉¤褰?===")

c.execute("SELECT order_no, status, plan_start, plan_end FROM production_orders WHERE order_no LIKE 'WO-202605%'")
rows = c.fetchall()
for r in rows:
    print(f"  {r['order_no']}: status={r['status']}, plan={r['plan_start']}~{r['plan_end']}")

c.execute("SELECT order_no, status FROM orders WHERE order_no LIKE 'WO-202605%'")
rows = c.fetchall()
for r in rows:
    print(f"  orders: {r['order_no']}: status={r['status']}")

conn.close()
print("\nMySQL 杩炴帴姝ｅ父 鉁?)
