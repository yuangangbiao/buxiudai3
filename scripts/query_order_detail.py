# -*- coding: utf-8 -*-
"""查询 ORD-20260416-0001 入库工序的详细数据"""
import pymysql

conn = pymysql.connect(
    host='localhost',
    user='root',
    password='88888888',
    database='steel_belt',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

order_no = 'ORD-20260416-0001'

print("=" * 60)
print(f"查询订单: {order_no}")
print("=" * 60)

with conn.cursor() as cursor:
    # 1. 查询 process_sub_steps 中这个订单的报工汇总
    cursor.execute("""
        SELECT order_no, step_name, SUM(quantity) as total_qty, COUNT(*) as cnt
        FROM process_sub_steps
        WHERE order_no = %s
        GROUP BY order_no, step_name
    """, (order_no,))
    rows = cursor.fetchall()
    print("\n【1】process_sub_steps 报工汇总:")
    for r in rows:
        print(f"  工序: {r['step_name']}, 总数量: {r['total_qty']}, 记录数: {r['cnt']}")

    # 2. 查询入库工序的详细报工记录
    cursor.execute("""
        SELECT id, order_no, step_name, quantity, operator, batch_no, created_at
        FROM process_sub_steps
        WHERE order_no = %s AND step_name = '入库'
        ORDER BY created_at DESC
        LIMIT 20
    """, (order_no,))
    rows = cursor.fetchall()
    print(f"\n【2】入库工序详细报工记录 (共{len(rows)}条，显示前20条):")
    for r in rows:
        print(f"  {r['created_at']} | 操作员: {r['operator']} | 数量: {r['quantity']} | 批次: {r['batch_no']}")

    # 3. 查询报工记录中的操作员分布
    cursor.execute("""
        SELECT operator, SUM(quantity) as total, COUNT(*) as cnt
        FROM process_sub_steps
        WHERE order_no = %s AND step_name = '入库'
        GROUP BY operator
        ORDER BY total DESC
    """, (order_no,))
    rows = cursor.fetchall()
    print(f"\n【3】入库工序操作员报工分布:")
    for r in rows:
        print(f"  {r['operator']}: 总数量={r['total']}, 次数={r['cnt']}")

    # 4. 查询 process_records 中的记录
    cursor.execute("""
        SELECT id, order_no, process_name, planned_qty, completed_qty, status
        FROM process_records
        WHERE order_no = %s
    """, (order_no,))
    rows = cursor.fetchall()
    print(f"\n【4】process_records 工序记录:")
    for r in rows:
        print(f"  工序: {r['process_name']}, 计划: {r['planned_qty']}, 完成: {r['completed_qty']}, 状态: {r['status']}")

    # 5. 查看入库工序是怎么同步过来的
    cursor.execute("""
        SELECT id, process_name, planned_qty, completed_qty, source, updated_at
        FROM process_records
        WHERE order_no = %s AND process_name = '入库'
    """, (order_no,))
    row = cursor.fetchone()
    if row:
        print(f"\n【5】入库工序同步详情:")
        print(f"  ID: {row['id']}")
        print(f"  计划量: {row['planned_qty']}")
        print(f"  完成量: {row['completed_qty']}")
        print(f"  来源: {row['source']}")
        print(f"  更新时间: {row['updated_at']}")

conn.close()
print("\n" + "=" * 60)
