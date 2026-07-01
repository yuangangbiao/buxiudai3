"""淇 WO-202605005 MySQL 鐘舵€佷负寰呮帓浜?""
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

c.execute("UPDATE production_orders SET status='寰呮帓浜?, updated_at=NOW() WHERE order_no=%s", (ORDER_NO,))
print(f"production_orders 宸叉洿鏂颁负 寰呮帓浜? 褰卞搷 {c.rowcount} 琛?)
conn.commit()

c.execute("SELECT order_no, status FROM production_orders WHERE order_no=%s", (ORDER_NO,))
po = c.fetchone()
print(f"楠岃瘉: {po['order_no']} status={po['status']}")
conn.close()
