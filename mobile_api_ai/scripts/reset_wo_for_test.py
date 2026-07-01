"""鍥為€€ WO-202605005 鍒板垵濮嬬姸鎬?寰呭彂甯?锛屽悓姝?MySQL"""
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

# 鍥為€€ production_orders
c.execute("UPDATE production_orders SET status='寰呭彂甯?, plan_start=NULL, plan_end=NULL, remark=NULL, updated_at=NOW() WHERE order_no=%s", (ORDER_NO,))
print(f"production_orders 宸查噸缃负 寰呭彂甯? 褰卞搷 {c.rowcount} 琛?)

# 鍥為€€ orders
c.execute("UPDATE orders SET status='寰呮帓浜?, updated_at=NOW() WHERE order_no=%s", (ORDER_NO,))
print(f"orders 宸查噸缃负 寰呮帓浜? 褰卞搷 {c.rowcount} 琛?)

conn.commit()

# 楠岃瘉
c.execute("SELECT order_no, status, plan_start, plan_end FROM production_orders WHERE order_no=%s", (ORDER_NO,))
po = c.fetchone()
print(f"\n楠岃瘉 production_orders: {po['order_no']} status={po['status']} plan={po['plan_start']}~{po['plan_end']}")

c.execute("SELECT order_no, status FROM orders WHERE order_no=%s", (ORDER_NO,))
o = c.fetchone()
print(f"楠岃瘉 orders:           {o['order_no']} status={o['status']}")

conn.close()
print("\n鉁?閲嶇疆瀹屾垚锛屽彲浠ュ紑濮嬫祴璇?)
