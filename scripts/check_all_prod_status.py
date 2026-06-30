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

# 1. 查看所有 production_orders 的状态分布
print("=== production_orders 状态分布 ===")
cursor.execute("SELECT status, COUNT(*) as cnt FROM production_orders GROUP BY status")
for row in cursor.fetchall():
    print(f"  {row['status']}: {row['cnt']}")

# 2. 查看所有 orders 的状态分布（非归档）
print("\n=== orders 状态分布（非归档）===")
cursor.execute("SELECT status, COUNT(*) as cnt FROM orders WHERE is_deleted=0 AND COALESCE(is_archived,0)=0 GROUP BY status")
for row in cursor.fetchall():
    print(f"  {row['status']}: {row['cnt']}")

# 3. 查看所有 production_orders 工单及其关联状态
print("\n=== 所有 production_orders 工单 ===")
cursor.execute("""
    SELECT po.id, po.order_no, po.status as po_status,
           o.order_no, o.status as order_status, COALESCE(o.is_archived, 0) as is_archived
    FROM production_orders po
    JOIN orders o ON po.order_id = o.id
    ORDER BY po.id
""")
results = cursor.fetchall()
print(f"总数: {len(results)}")
for r in results:
    print(f"  ID={r['id']}, WO={r['order_no']}, PO_status={r['po_status']}, Order={r['order_no']}, Order_status={r['order_status']}, Archived={r['is_archived']}")

# 4. 模拟 process_view 的查询逻辑
print("\n=== 模拟 process_view 查询（无关键词）===")
print("逻辑：先查'生产中'，没有则查'待开始'，再没有则查'已完成'")

cursor.execute("""
    SELECT po.id, po.order_no, po.status, o.order_no
    FROM production_orders po
    JOIN orders o ON po.order_id = o.id
    WHERE 1=1
    AND o.status NOT IN ('已发货', '已取消')
    AND COALESCE(o.is_archived, 0) = 0
    AND po.status = '生产中'
""")
results = cursor.fetchall()
print(f"'生产中' 工单数: {len(results)}")
for r in results:
    print(f"  {r['order_no']} -> {r['order_no']}")

cursor.execute("""
    SELECT po.id, po.order_no, po.status, o.order_no
    FROM production_orders po
    JOIN orders o ON po.order_id = o.id
    WHERE 1=1
    AND o.status NOT IN ('已发货', '已取消')
    AND COALESCE(o.is_archived, 0) = 0
    AND po.status = '待开始'
""")
results = cursor.fetchall()
print(f"'待开始' 工单数: {len(results)}")
for r in results:
    print(f"  {r['order_no']} -> {r['order_no']}")

cursor.execute("""
    SELECT po.id, po.order_no, po.status, o.order_no
    FROM production_orders po
    JOIN orders o ON po.order_id = o.id
    WHERE 1=1
    AND o.status NOT IN ('已发货', '已取消')
    AND COALESCE(o.is_archived, 0) = 0
    AND po.status = '已完成'
""")
results = cursor.fetchall()
print(f"'已完成' 工单数: {len(results)}")
for r in results:
    print(f"  {r['order_no']} -> {r['order_no']}")

conn.close()
print("\n完成!")