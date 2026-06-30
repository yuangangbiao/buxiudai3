# -*- coding: utf-8 -*-
"""检查可用订单和工序数据 - 用于测试报工"""
import pymysql

STEEL_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '88888888',
    'database': 'steel_belt', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

conn = pymysql.connect(**STEEL_CONFIG)
try:
    with conn.cursor() as c:
        # 1. 查看现有 process_records 中未完成的工序（适合测试报工）
        c.execute("""
            SELECT order_no, process_name, completed_qty, planned_qty, status
            FROM process_records
            WHERE status IN ('pending', 'in_progress')
              AND order_no != ''
              AND order_no IS NOT NULL
            ORDER BY order_no, process_name
        """)
        rows = c.fetchall()
        print(f"=== 可测试的工序（未完成、有订单号）: {len(rows)} 条 ===")
        for r in rows:
            print(f"  {r['order_no']}/{r['process_name']}: "
                  f"完成={r['completed_qty']}, 计划={r['planned_qty']}, 状态={r['status']}")

        # 2. 检查所有 order 对应的 production_id 映射
        c.execute("""
            SELECT DISTINCT pr.order_no, pr.production_id, po.id as po_id
            FROM process_records pr
            LEFT JOIN production_orders po ON pr.production_id = po.id
            WHERE pr.order_no != '' AND pr.order_no IS NOT NULL
            ORDER BY pr.order_no
        """)
        rows = c.fetchall()
        print(f"\n=== 订单与 production_id 映射: {len(rows)} 条 ===")
        for r in rows:
            print(f"  order_no={r['order_no']}, production_id={r['production_id']}, po.id={r['po_id']}")

        # 3. 检查 process_sub_steps 当前报工记录
        c.execute("""
            SELECT order_no, step_name, SUM(quantity) as total_qty, COUNT(*) as cnt
            FROM process_sub_steps
            GROUP BY order_no, step_name
            ORDER BY order_no, step_name
        """)
        rows = c.fetchall()
        print(f"\n=== process_sub_steps 当前报工汇总: {len(rows)} 条 ===")
        for r in rows:
            print(f"  {r['order_no']}/{r['step_name']}: {r['cnt']}次, {r['total_qty']}件")

        # 4. 查看 ORD-202604210002 的 process_records 详情（有真实报工数据）
        c.execute("""
            SELECT id, order_no, production_id, process_name, process_code,
                   completed_qty, planned_qty, status, flow_type, unit
            FROM process_records
            WHERE order_no = 'ORD-202604210002'
            ORDER BY process_seq
        """)
        rows = c.fetchall()
        print(f"\n=== ORD-202604210002 工序详情: {len(rows)} 条 ===")
        for r in rows:
            print(f"  id={r['id']}, process={r['process_name']}({r['process_code']}), "
                  f"完成={r['completed_qty']}, 计划={r['planned_qty']}, "
                  f"状态={r['status']}, flow_type={r['flow_type']}")

finally:
    conn.close()
