"""鍒楀嚭 orders 鍜?production_orders 鐨勫畬鏁村搴斿叧绯?""
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

print(f'{"orders.id":>4s} | {"order_no":22s} | {"status":8s} | prod_id(鑻ユ湁)')
print('-' * 55)

# 鍏堝湪 production_orders 涓煡璇㈡墍鏈?order_id 瀵瑰簲鐨?prod_id
c.execute("SELECT id as prod_id, order_id, order_no FROM production_orders")
prod_map = {r['order_id']: (r['prod_id'], r['order_no']) for r in c.fetchall()}

# 鍒楀嚭鎵€鏈?orders锛堟湭鍒犻櫎鐨勶級
c.execute("""
    SELECT id, order_no, status, is_deleted
    FROM orders
    WHERE is_deleted = 0
    ORDER BY id
""")
orders = c.fetchall()

for o in orders:
    prod_info = prod_map.get(o['id'])
    if prod_info:
        pid, wo = prod_info
        print(f'{o["id"]:>4d} | {o["order_no"]:22s} | {o["status"]:8s} | prod_id={pid} ({wo})')
    else:
        print(f'{o["id"]:>4d} | {o["order_no"]:22s} | {o["status"]:8s} | -')

print()
print()
print('=' * 55)
print('production_orders 瀹屾暣鍒楄〃:')
print(f'{"prod_id":>4s} | {"order_no":18s} | {"order_id":>4s} | {"status":8s}')
print('-' * 55)

c.execute("""
    SELECT id, order_no, order_id, status
    FROM production_orders
    ORDER BY id
""")
prods = c.fetchall()
for p in prods:
    print(f'{p["id"]:>4d} | {p["order_no"]:18s} | {p["order_id"]:>4d} | {p["status"]:8s}')

conn.close()
