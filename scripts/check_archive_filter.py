# -*- coding: utf-8 -*-
import sys
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_DIR, '.env'))

import pymysql

conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database=os.getenv('MYSQL_DATABASE', 'steel_belt'),
    charset='utf8mb4'
)

cursor = conn.cursor(pymysql.cursors.DictCursor)

# 查看订单 17 的完整信息
print("=== 订单 17 完整信息 ===")
cursor.execute("SELECT * FROM orders WHERE id = 17")
order = cursor.fetchone()
for k, v in order.items():
    print(f"  {k}: {v}")

# 模拟 get_all_with_order 的查询
print("\n=== 模拟工序追踪下拉查询 ===")
cursor.execute("""
    SELECT po.*, o.order_no
    FROM production_orders po
    JOIN orders o ON po.order_id = o.id
    WHERE 1=1
    AND o.status != '已发货'
    AND COALESCE(o.is_archived, 0) = 0
    AND po.status IN ('生产中')
    ORDER BY po.priority ASC
""")
results = cursor.fetchall()
print(f"生产中工单数量: {len(results)}")
for r in results:
    print(f"  工单ID={r['id']}, 订单号={r['order_no']}, 订单={r['order_no']}")

# 尝试不过滤归档
print("\n=== 不过滤归档的查询 ===")
cursor.execute("""
    SELECT po.*, o.order_no, o.status as order_status, o.is_archived
    FROM production_orders po
    JOIN orders o ON po.order_id = o.id
    WHERE 1=1
    AND po.status IN ('生产中')
    ORDER BY po.priority ASC
""")
results = cursor.fetchall()
print(f"生产中工单数量: {len(results)}")
for r in results:
    print(f"  工单ID={r['id']}, 订单号={r['order_no']}, 订单={r['order_no']}, order_status={r['order_status']}, is_archived={r['is_archived']}")

conn.close()