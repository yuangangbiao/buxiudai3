# -*- coding: utf-8 -*-
"""
生产状态检查脚本
查看工单状态及其关联订单的归档状态
用于检查生产工单和订单的一致性
"""
import sys
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_DIR, '.env'))

import pymysql

# 建立数据库连接
conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database=os.getenv('MYSQL_DATABASE', 'steel_belt'),
    charset='utf8mb4'
)

cursor = conn.cursor(pymysql.cursors.DictCursor)

# 查看订单17的归档状态
cursor.execute("SELECT id, order_no, status, is_archived FROM orders WHERE id = 17")
order = cursor.fetchone()
print(f"订单 17: status={order['status']}, is_archived={order['is_archived']}")

# 查看所有"生产中"工单及其订单状态
cursor.execute("""
    SELECT po.id, po.order_no, po.status as po_status, o.order_no, o.status as order_status, o.is_archived
    FROM production_orders po
    JOIN orders o ON po.order_id = o.id
    WHERE po.status = '生产中'
""")
results = cursor.fetchall()
print(f"\n'生产中' 工单数量: {len(results)}")
for r in results:
    print(f"  工单ID={r['id']}, 订单号={r['order_no']}, 订单={r['order_no']}, 订单状态={r['order_status']}, is_archived={r['is_archived']}")

# 查看"待开始"状态的工单
cursor.execute("""
    SELECT po.id, po.order_no, po.status as po_status, o.order_no, o.status as order_status, o.is_archived
    FROM production_orders po
    JOIN orders o ON po.order_id = o.id
    WHERE po.status = '待开始'
""")
results = cursor.fetchall()
print(f"\n'待开始' 工单数量: {len(results)}")
for r in results:
    print(f"  工单ID={r['id']}, 订单号={r['order_no']}, 订单={r['order_no']}, 订单状态={r['order_status']}, is_archived={r['is_archived']}")

conn.close()