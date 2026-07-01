"""妫€鏌?WO-202605005 鍦ㄥ悇琛ㄧ殑鐘舵€?""
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

conn = pymysql.connect(**cfg, cursorclass=DictCursor)
c = conn.cursor()

ORDER_NO = 'WO-202605005'

print("=== production_orders ===")
c.execute("SELECT * FROM production_orders WHERE order_no=%s", (ORDER_NO,))
row = c.fetchone()
if row:
    for k, v in row.items():
        print(f"  {k}: {v}")
else:
    print("  NOT FOUND")

print()
print("=== orders ===")
c.execute("SELECT * FROM orders WHERE order_no=%s", (ORDER_NO,))
row = c.fetchone()
if row:
    for k, v in row.items():
        print(f"  {k}: {v}")
else:
    print("  NOT FOUND")

print()
print("=== 鎵€鏈夎〃 ===")
c.execute("SHOW TABLES")
tables = [r.values() for r in c.fetchall()]
for t in sorted(tables):
    list_t = list(t)
    print(f"  {list_t[0]}")

conn.close()
