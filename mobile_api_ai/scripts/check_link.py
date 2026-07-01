"""妫€鏌?orders(id=9, ORD-202604210003) 涓?WO-202605005 鐨勫叧鑱?""
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

print("=== 鍏抽敭鍏宠仈鍏崇郴 ===")
c.execute("SELECT id, order_no, order_id, status FROM production_orders WHERE order_no='WO-202605005'")
po = c.fetchone()
print(f"production_orders: id={po['id']}, order_no={po['order_no']}, order_id={po['order_id']}, status={po['status']}")

c.execute("SELECT id, order_no, status FROM orders WHERE id=%s", (po['order_id'],))
o = c.fetchone()
print(f"orders(id={po['order_id']}): order_no={o['order_no']}, status={o['status']} 鈫?涓昏蒋浠跺彲鑳界湅杩欎釜!")

c.execute("SELECT id, order_no, status FROM orders WHERE order_no='WO-202605005'")
w = c.fetchone()
if w:
    print(f"orders(WO-202605005): id={w['id']}, status={w['status']} 鈫?鏂版彃鍏ョ殑璁板綍")
else:
    print(f"orders(WO-202605005): 涓嶅瓨鍦?)

print()
print("=== 缁撹 ===")
print(f"WO-202605005 鍏宠仈鐨勬槸 orders(id={po['order_id']}, order_no={o['order_no']})")
print(f"涓昏蒋浠惰鐪嬬殑搴旇鏄?orders(id={po['order_id']}) 鐨勭姸鎬侊紝鑰屼笉鏄?WO-202605005")
print(f"褰撳墠 orders(id={po['order_id']}) 鐨勭姸鎬? {o['status']}")
print(f"闇€瑕佺殑鐘舵€? {po['status']}")

# 鍚屾
if o['status'] != po['status']:
    c.execute("UPDATE orders SET status=%s, updated_at=NOW() WHERE id=%s", (po['status'], po['order_id']))
    conn.commit()
    print(f"\n鉁?宸插悓姝?orders(id={po['order_id']}) 鐘舵€? {o['status']} 鈫?{po['status']}")
else:
    print(f"\n鐘舵€佸凡涓€鑷达紝鏃犻渶鏇存柊")

# 楠岃瘉 orders(id=9) 鏈€鏂扮姸鎬?c.execute("SELECT id, order_no, status, updated_at FROM orders WHERE id=%s", (po['order_id'],))
o2 = c.fetchone()
print(f"orders now: id={o2['id']}, order_no={o2['order_no']}, status={o2['status']}")

conn.close()
