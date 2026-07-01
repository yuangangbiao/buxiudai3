"""瀹屾暣灞曠ず WO-202605005 鐨勬暟鎹叧鑱斿叧绯?""
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

print('=== 1. production_orders 涓?WO-202605005 ===')
c.execute("SELECT id, order_no, order_id, status FROM production_orders WHERE order_no='WO-202605005'")
po = c.fetchone()
print(f'  id={po["id"]}, order_no={po["order_no"]}, order_id={po["order_id"]}, status={po["status"]}')

print()
print(f'=== 2. order_id={po["order_id"]} 鎸囧悜鐨?orders 璁板綍 ===')
c.execute("SELECT id, order_no, status FROM orders WHERE id=%s", (po['order_id'],))
o = c.fetchone()
print(f'  id={o["id"]}, order_no={o["order_no"]}, status={o["status"]}')
print(f'  鈫?杩欐槸瀹㈡埛璁㈠崟 ORD-202604210003')

print()
print(f'=== 3. orders 琛ㄤ腑 WO-202605005 鐨勮褰?===')
c.execute("SELECT id, order_no, status FROM orders WHERE order_no='WO-202605005'")
wo = c.fetchone()
if wo:
    print(f'  id={wo["id"]}, order_no={wo["order_no"]}, status={wo["status"]}')
    print(f'  鈫?杩欐槸宸ュ崟璁板綍锛屼絾鏄?production_orders 骞舵病鏈夊叧鑱斿埌杩欐潯璁板綍锛?)
else:
    print(f'  orders 琛ㄤ腑娌℃湁 WO-202605005 鐨勮褰?)

print()
print('=== 褰撳墠閿欒鍏宠仈 ===')
print(f'  production_orders.order_id={po["order_id"]} 鈫?orders(id={o["id"]}, {o["order_no"]})')
print(f'  浣嗗伐鍗?WO-202605005 鑷繁搴旇鍏宠仈鍒?orders(id={wo["id"]}, {wo["order_no"]})')
print()
print(f'=== 搴旇淇涓?===')
print(f'  production_orders.order_id={po["order_id"]} 鈫?orders(id={wo["id"]}, {wo["order_no"]})')

conn.close()
