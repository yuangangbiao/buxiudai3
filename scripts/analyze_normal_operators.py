# -*- coding: utf-8 -*-
"""分析"正常"操作员是否是真实生产数据"""
import pymysql

STEEL_BELT_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '88888888',
    'database': 'steel_belt', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

conn = pymysql.connect(**STEEL_BELT_CONFIG)
try:
    with conn.cursor() as c:
        # 所有 operators 分类
        c.execute("""
            SELECT 
                CASE 
                    WHEN operator LIKE 'stress-%%' THEN 'stress-* (压测)'
                    WHEN operator LIKE '8008-stress-%%' THEN '8008-stress-* (同步压测)'
                    WHEN operator LIKE '5008-stress-%%' THEN '5008-stress-* (报工压测)'
                    WHEN operator LIKE '5srv-%%' THEN '5srv-* (服务压测)'
                    WHEN operator LIKE 'dup-test-%%' THEN 'dup-test-* (测试)'
                    WHEN operator LIKE '8008-test-%%' THEN '8008-test-* (测试)'
                    ELSE '其他/真正的操作员'
                END as category,
                COUNT(*) as cnt,
                SUM(quantity) as total_qty
            FROM process_sub_steps
            GROUP BY category
            ORDER BY cnt DESC
        """)
        rows = c.fetchall()
        print("=== process_sub_steps 操作员分类 ===")
        for r in rows:
            print(f"  {r['category']}: {r['cnt']}条, {r['total_qty']}件")

        # 看看"其他"到底是什么
        c.execute("""
            SELECT operator, COUNT(*) as cnt
            FROM process_sub_steps
            WHERE operator NOT LIKE 'stress-%%'
              AND operator NOT LIKE '8008-stress-%%'
              AND operator NOT LIKE '5008-stress-%%'
              AND operator NOT LIKE '5srv-%%'
              AND operator NOT LIKE 'dup-test-%%'
              AND operator NOT LIKE '8008-test-%%'
            GROUP BY operator
            ORDER BY cnt DESC
        """)
        rows = c.fetchall()
        print(f"\n=== 真正操作员 ({len(rows)}个) ===")
        for r in rows:
            print(f"  {r['operator']}: {r['cnt']}条")

        # 非测试数据在各订单/工序的分布
        c.execute("""
            SELECT order_no, step_name, SUM(quantity) as total_qty
            FROM process_sub_steps
            WHERE operator NOT LIKE 'stress-%%'
              AND operator NOT LIKE '8008-stress-%%'
              AND operator NOT LIKE '5008-stress-%%'
              AND operator NOT LIKE '5srv-%%'
              AND operator NOT LIKE 'dup-test-%%'
              AND operator NOT LIKE '8008-test-%%'
            GROUP BY order_no, step_name
            ORDER BY order_no, step_name
        """)
        rows = c.fetchall()
        print(f"\n=== 真正生产数据分布 ===")
        for r in rows:
            print(f"  {r['order_no']}/{r['step_name']}: {r['total_qty']}件")

        total_production = sum(r['total_qty'] for r in rows)
        print(f"\n  真正生产数据总数量: {total_production}")

        # 看看 process_records 中其他订单
        c.execute("""
            SELECT order_no, process_name, completed_qty, status
            FROM process_records
            ORDER BY order_no
        """)
        rows = c.fetchall()
        print(f"\n=== process_records 全部记录 ===")
        for r in rows:
            print(f"  {r['order_no']}/{r['process_name']}: 完成={r['completed_qty']} 状态={r['status']}")

finally:
    conn.close()
