"""琛ュ叏 WO-202605005 鍒?orders 琛?""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('d:/yuan/涓嶉攬閽㈢綉甯﹁窡鍗?.0/mobile_api_ai/.env')

import os, pymysql
from datetime import datetime
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
NOW = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 1. 鍏堟鏌ユ槸鍚﹀凡瀛樺湪
c.execute("SELECT id, status FROM orders WHERE order_no=%s", (ORDER_NO,))
existing = c.fetchone()
if existing:
    print(f"WO-202605005 宸插瓨鍦?orders 琛?(id={existing['id']}, status={existing['status']})锛岃烦杩囨彃鍏?)
else:
    # 浠?ORD-202604210003 澶嶅埗瀹㈡埛淇℃伅锛屼粠 dispatch_center 鍙栦骇鍝佷俊鎭?    sql = """INSERT INTO orders (
        order_no, customer_name, customer_phone, customer_address,
        product_type, material, quantity, unit, unit_price, total_amount,
        status, priority_level, order_source, created_at, updated_at,
        is_deleted, version, is_archived
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    vals = (
        ORDER_NO,
        '灞变笢寰峰窞鑷姩鏈烘璁惧鍏徃',  # 浠?ORD-202604210003 澶嶅埗
        '', '',                      # phone, address
        '涓嶉攬閽㈢綉甯?,                # product_type
        '304涓嶉攬閽?,                 # material
        1, '绫?,                     # quantity, unit
        0.00, 0.00,                  # unit_price, total_amount
        '鐢熶骇涓?,                    # status - 鍖归厤 dispatch_center 褰撳墠鐘舵€?        '涓?, '绾夸笅',                # priority_level, order_source
        NOW, NOW,                    # created_at, updated_at
        0, 1, 0                      # is_deleted, version, is_archived
    )
    c.execute(sql, vals)
    conn.commit()
    print(f"WO-202605005 宸叉彃鍏?orders 琛? 褰卞搷 {c.rowcount} 琛?)

# 楠岃瘉
c.execute("SELECT id, order_no, status, created_at FROM orders WHERE order_no LIKE %s ORDER BY id", ('%605005%',))
for r in c.fetchall():
    print(f"  楠岃瘉: id={r['id']} order_no={r['order_no']} status={r['status']}")

conn.close()
