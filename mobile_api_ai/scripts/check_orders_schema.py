"""妫€鏌?orders 琛ㄧ粨鏋勫強 WO-202605005 鍏宠仈鐨?order_id=9"""
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

# orders 琛ㄧ粨鏋?print("=== orders 琛ㄧ粨鏋?===")
c.execute("DESCRIBE orders")
for row in c.fetchall():
    print(f"  {row}")

# 妫€鏌?order_id=9 鏄惁瀛樺湪
print()
print("=== orders WHERE id=9 ===")
c.execute("SELECT * FROM orders WHERE id=9")
row = c.fetchone()
if row:
    for k, v in row.items():
        print(f"  {k}: {v}")
else:
    print("  NOT FOUND")

# 妫€鏌ユ墍鏈?orders 璁板綍
print()
print("=== 鎵€鏈?orders ===")
c.execute("SELECT id, order_no, status, created_at FROM orders ORDER BY id")
for row in c.fetchall():
    print(f"  id={row['id']} order_no={row['order_no']} status={row['status']} created_at={row['created_at']}")

# 妫€鏌?production_orders 琛ㄧ粨鏋?print()
print("=== production_orders 琛ㄧ粨鏋?===")
c.execute("DESCRIBE production_orders")
for row in c.fetchall():
    print(f"  {row}")

conn.close()
