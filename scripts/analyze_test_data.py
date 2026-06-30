# -*- coding: utf-8 -*-
"""分析测试数据的范围、分布和影响"""
import pymysql

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '88888888',
    'database': 'container_center',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

STEEL_BELT_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '88888888',
    'database': 'steel_belt',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_conn(db='container_center'):
    config = STEEL_BELT_CONFIG if db == 'steel_belt' else DB_CONFIG
    return pymysql.connect(**config)


def analyze_process_sub_steps():
    print("\n" + "=" * 60)
    print("【1】process_sub_steps 测试数据分析 (steel_belt)")
    print("=" * 60)
    conn = get_conn('steel_belt')
    try:
        with conn.cursor() as c:
            # 总记录数
            c.execute("SELECT COUNT(*) as cnt FROM process_sub_steps")
            total = c.fetchone()['cnt']
            print(f"  总记录数: {total}")

            # 测试数据总数 (operator 以 stress 开头)
            c.execute("SELECT COUNT(*) as cnt FROM process_sub_steps WHERE operator LIKE 'stress-%'")
            stress_cnt = c.fetchone()['cnt']
            print(f"  测试数据 (operator LIKE 'stress-%%'): {stress_cnt}")

            # 测试数据按操作员分布
            c.execute("""
                SELECT operator, COUNT(*) as cnt, SUM(quantity) as total_qty
                FROM process_sub_steps
                WHERE operator LIKE 'stress-%'
                GROUP BY operator
                ORDER BY cnt DESC
            """)
            rows = c.fetchall()
            print(f"\n  测试数据操作员分布:")
            for r in rows:
                print(f"    {r['operator']}: {r['cnt']}条, 共{r['total_qty']}件")

            # 测试数据按工序分布
            c.execute("""
                SELECT step_name, COUNT(*) as cnt, SUM(quantity) as total_qty
                FROM process_sub_steps
                WHERE operator LIKE 'stress-%'
                GROUP BY step_name
                ORDER BY cnt DESC
            """)
            rows = c.fetchall()
            print(f"\n  测试数据工序分布:")
            for r in rows:
                print(f"    {r['step_name']}: {r['cnt']}条, 共{r['total_qty']}件")

            # 测试数据按订单分布 (Top 10)
            c.execute("""
                SELECT order_no, COUNT(*) as cnt, SUM(quantity) as total_qty
                FROM process_sub_steps
                WHERE operator LIKE 'stress-%'
                GROUP BY order_no
                ORDER BY cnt DESC
                LIMIT 10
            """)
            rows = c.fetchall()
            print(f"\n  测试数据订单分布 (Top 10):")
            for r in rows:
                print(f"    {r['order_no']}: {r['cnt']}条, 共{r['total_qty']}件")

            # 正常数据总数
            normal_cnt = total - stress_cnt
            print(f"\n  正常数据: {normal_cnt}")
            print(f"  测试数据占比: {stress_cnt/total*100:.1f}%" if total > 0 else "  N/A")
            return stress_cnt
    finally:
        conn.close()


def analyze_process_records():
    print("\n" + "=" * 60)
    print("【2】process_records 受测试数据影响分析 (steel_belt)")
    print("=" * 60)
    conn = get_conn('steel_belt')
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) as cnt FROM process_records")
            total = c.fetchone()['cnt']
            print(f"  总记录数: {total}")

            # 找出哪些 process_records 的 order_no 也存在于测试数据中
            c.execute("""
                SELECT pr.order_no, pr.process_name, pr.completed_qty,
                       (SELECT SUM(quantity) FROM process_sub_steps pss
                        WHERE pss.order_no = pr.order_no
                          AND pss.step_name = pr.process_name
                          AND pss.operator LIKE 'stress-%') as test_qty
                FROM process_records pr
                WHERE EXISTS (
                    SELECT 1 FROM process_sub_steps pss
                    WHERE pss.order_no = pr.order_no
                      AND pss.operator LIKE 'stress-%'
                )
                ORDER BY pr.order_no, pr.process_name
            """)
            rows = c.fetchall()
            print(f"\n  受测试数据影响的 process_records ({len(rows)}条):")
            total_test_qty = 0
            for r in rows:
                test_qty = r['test_qty'] or 0
                total_test_qty += test_qty
                if test_qty > 0:
                    print(f"    {r['order_no']}/{r['process_name']}: "
                          f"当前完成量={r['completed_qty']}, 含测试数据={test_qty}")
            print(f"\n  测试数据贡献总数量: {total_test_qty}")

            # 受影响的订单列表
            c.execute("""
                SELECT DISTINCT pr.order_no
                FROM process_records pr
                WHERE EXISTS (
                    SELECT 1 FROM process_sub_steps pss
                    WHERE pss.order_no = pr.order_no
                      AND pss.operator LIKE 'stress-%'
                )
            """)
            affected_orders = [r['order_no'] for r in c.fetchall()]
            print(f"  受影响订单数: {len(affected_orders)}")
            if affected_orders:
                print(f"  受影响订单列表: {', '.join(affected_orders)}")
            return total_test_qty, affected_orders
    finally:
        conn.close()


def analyze_report_queue():
    print("\n" + "=" * 60)
    print("【3】report_queue 测试数据分析 (container_center)")
    print("=" * 60)
    conn = get_conn('container_center')
    try:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) as cnt FROM report_queue")
            total = c.fetchone()['cnt']
            print(f"  总记录数: {total}")

            c.execute("""
                SELECT status, COUNT(*) as cnt
                FROM report_queue
                GROUP BY status
            """)
            rows = c.fetchall()
            print(f"  队列状态分布:")
            for r in rows:
                print(f"    {r['status']}: {r['cnt']}")

            c.execute("""
                SELECT COUNT(*) as cnt
                FROM report_queue rq
                WHERE rq.order_no IN (
                    SELECT DISTINCT order_no FROM steel_belt.process_sub_steps
                    WHERE operator LIKE 'stress-%'
                )
            """)
            affected = c.fetchone()['cnt']
            print(f"  与测试数据关联的队列记录: {affected}")
            return affected
    finally:
        conn.close()


def analyze_quality_records():
    print("\n" + "=" * 60)
    print("【4】其他独立表测试数据分析 (steel_belt)")
    print("=" * 60)
    conn = get_conn('steel_belt')
    try:
        with conn.cursor() as c:
            for table in ['quality_records', 'material_records', 'outsource_records',
                          'repair_records', 'schedule_records']:
                c.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                cnt = c.fetchone()['cnt']
                has_operator = False
                try:
                    c.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE operator LIKE 'stress-%'")
                    stress_cnt = c.fetchone()['cnt']
                    has_operator = True
                except Exception:
                    stress_cnt = 0
                if has_operator:
                    print(f"  {table}: 共{cnt}条, 测试数据{stress_cnt}条")
                else:
                    print(f"  {table}: 共{cnt}条 (无 operator 字段)")
    finally:
        conn.close()


def main():
    print("=" * 60)
    print("测试数据特征分析")
    print("执行时间: 2026-06-20")
    print("=" * 60)

    stress_cnt = analyze_process_sub_steps()
    analyze_process_records()
    analyze_report_queue()
    analyze_quality_records()

    print("\n" + "=" * 60)
    print("分析总结")
    print("=" * 60)
    print(f"  核心问题: process_sub_steps 中有 {stress_cnt} 条测试数据")
    print(f"  影响: process_records 的 completed_qty 被虚高")
    print(f"  需要备份后清除测试数据，并重新计算 process_records")
    print("=" * 60)


if __name__ == '__main__':
    main()
