"""绮剧‘鏌ヨ orders 琛ㄤ腑鎵€鏈夊寘鍚?WO-202605005 鐨勮褰?""
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

# 妯＄硦鎼滅储鍖呭惈 605005 鐨勮褰?print("=== orders LIKE %605005% ===")
c.execute("SELECT * FROM orders WHERE order_no LIKE %s", ('%605005%',))
rows = c.fetchall()
if rows:
    for r in rows:
        print(f"  id={r['id']} order_no={r['order_no']} status={r['status']}")
        print(f"  product_name={r.get('product_name','')}")
        print(f"  created_at={r.get('created_at','')}")
else:
    print("  NOT FOUND")

# 鎼滅储 WO-2026
print()
print("=== orders LIKE %WO-2026% ===")
c.execute("SELECT id, order_no, status, created_at FROM orders WHERE order_no LIKE %s ORDER BY id", ('%WO-2026%',))
rows = c.fetchall()
if rows:
    for r in rows:
        print(f"  id={r['id']} order_no={r['order_no']} status={r['status']} created_at={r['created_at']}")
else:
    print("  NOT FOUND")

# 鍏ㄩ儴 orders锛堥檺100锛?print()
print("=== 鍏ㄩ儴 orders锛坕d+order_no+status锛?==")
c.execute("SELECT id, order_no, status, created_at FROM orders ORDER BY id")
rows = c.fetchall()
if rows:
    for r in rows:
        print(f"  id={r['id']:>3} order_no={r['order_no']:<25} status={r['status']}")

conn.close()
