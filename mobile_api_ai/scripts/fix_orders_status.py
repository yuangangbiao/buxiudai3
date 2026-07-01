"""淇 orders 琛ㄤ腑鍏宠仈宸ュ崟鐨勭姸鎬?""
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

# 1. 閫氳繃 order_id 鎵惧埌鍏宠仈鐨?orders 璁板綍
c.execute("SELECT order_id, order_no, status FROM production_orders WHERE order_no='WO-202605005'")
po = c.fetchone()
print(f"production_orders: order_id={po['order_id']}, order_no={po['order_no']}, status={po['status']}")

# 2. 鏇存柊 orders 琛ㄤ腑瀵瑰簲鐨勮褰?order_id = po['order_id']
c.execute("SELECT id, order_no, status FROM orders WHERE id=%s", (order_id,))
o = c.fetchone()
print(f"orders before: id={o['id']}, order_no={o['order_no']}, status={o['status']}")

# 鐘舵€佹槧灏? 鍙宸ュ崟杩涘叆娴佺▼锛宱rders 鐘舵€佹敼涓?"宸叉帓浜?
c.execute("UPDATE orders SET status='宸叉帓浜?, updated_at=NOW() WHERE id=%s", (order_id,))
conn.commit()
print(f"orders 宸叉洿鏂? 褰卞搷 {c.rowcount} 琛?)

# 楠岃瘉
c.execute("SELECT id, order_no, status FROM orders WHERE id=%s", (order_id,))
o = c.fetchone()
print(f"orders after: id={o['id']}, order_no={o['order_no']}, status={o['status']}")

conn.close()
