"""琛ュ叏 WO-202605005 鍒?orders 琛?""
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

# 1. 鍏堢湅 orders(id=9, ORD-202604210003) 鐨勫畬鏁存暟鎹紝鐢ㄦ潵鍙傝€?print("=== orders id=9锛堣幏鍙栧畬鏁村瓧娈靛弬鑰冿級===")
c.execute("SELECT * FROM orders WHERE id=9")
order9 = c.fetchone()
for k, v in order9.items():
    print(f"  {k}: {v}")

# 2. 鐪?orders(id=20, WO-202605004) 鐨勫畬鏁存暟鎹紝浣滀负 WO 宸ュ崟鐨勫弬鑰?print()
print("=== orders id=20锛圵O-202605004锛屼綔涓篧O宸ュ崟鍙傝€冿級===")
c.execute("SELECT * FROM orders WHERE id=20")
order20 = c.fetchone()
if order20:
    for k, v in order20.items():
        print(f"  {k}: {v}")

# 3. 鐪?production_orders 閲?WO-202605005 鐨勫畬鏁存暟鎹?print()
print("=== production_orders 涓?WO-202605005 ===")
c.execute("SELECT * FROM production_orders WHERE order_no='WO-202605005'")
po = c.fetchone()
if po:
    for k, v in po.items():
        print(f"  {k}: {v}")

# 4. 妫€鏌?orders 琛ㄦ渶澶?id
print()
print("=== orders 琛?max id ===")
c.execute("SELECT MAX(id) as max_id FROM orders")
print(f"  max_id={c.fetchone()['max_id']}")

conn.close()
