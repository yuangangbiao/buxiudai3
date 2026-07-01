"""楠岃瘉涓昏蒋浠跺簲璇ヨ兘鐪嬪埌鐨勬暟鎹?""
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

# 涓昏蒋浠剁殑鏍稿績鏌ヨ: production_orders JOIN orders ON order_no = order_no
c.execute("""
    SELECT po.order_no, po.status as prod_status, po.order_id,
           o.id, o.order_no, o.status as order_status
    FROM production_orders po
    JOIN orders o ON po.order_no = o.order_no
    WHERE po.order_no = 'WO-202605005'
""")
r = c.fetchone()
print('=== 涓昏蒋浠?get_all_with_order 鏌ヨ缁撴灉 ===')
print(f'宸ュ崟鍙? {r["order_no"]}')
print(f'production_orders.status: {r["prod_status"]}')
print(f'JOIN orders.id: {r["id"]}')
print(f'JOIN orders.order_no: {r["order_no"]}')
print(f'JOIN orders.status: {r["order_status"]}')
print()
print('=== 涓昏蒋浠剁湅鍒扮殑鏁版嵁 ===')
print(f'  宸ュ崟 WO-202605005 -> 鍏宠仈璁㈠崟 {r["order_no"]}')
print(f'  production_orders 鐘舵€? {r["prod_status"]}')
print(f'  orders(id={r["id"]}) 鐘舵€? {r["order_status"]}')
print()
print('涓ゅ彞鍧囧凡姝ｇ‘鏇存柊锛屽鏋滀富杞欢娌″彉鍖栵紝璇峰埛鏂版垨閲嶅惎')

# 涔熸鏌ュ叏閮?production_orders 鐨勫畬鏁村垪琛?print()
print('=== 涓昏蒋浠跺伐鍗曞垪琛ㄥ簲鏄剧ず鐨勬暟鎹?===')
c.execute("""
    SELECT po.order_no, o.order_no, o.customer_name,
           o.product_type, o.quantity, po.status
    FROM production_orders po
    JOIN orders o ON po.order_no = o.order_no
    WHERE o.status NOT IN ('宸插彂璐?, '宸插彇娑?)
      AND po.status != '宸插彇娑?
      AND COALESCE(o.is_archived, 0) = 0
    ORDER BY po.id DESC
    LIMIT 10
""")
for row in c.fetchall():
    print(f'  {row["order_no"]:16s} | {row["order_no"]:20s} | {row["customer_name"]:8s} | {row["status"]}')

conn.close()
