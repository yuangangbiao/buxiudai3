# -*- coding: utf-8 -*-
"""补充分析：正常数据详情 + 其他测试操作员模式"""
import pymysql

STEEL_BELT_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '88888888',
    'database': 'steel_belt',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

CC_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '88888888',
    'database': 'container_center',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_conn(db='steel_belt'):
    c = STEEL_BELT_CONFIG if db == 'steel_belt' else CC_CONFIG
    return pymysql.connect(**c)


def analyze_normal_data():
    """分析 process_sub_steps 中的正常数据"""
    conn = get_conn('steel_belt')
    try:
        with conn.cursor() as c:
            # 1. 非测试数据的操作员分布
            c.execute("""
                SELECT operator, COUNT(*) as cnt, SUM(quantity) as total_qty
                FROM process_sub_steps
                WHERE operator NOT LIKE 'stress-%'
                  AND operator NOT LIKE '8008-stress-%'
                GROUP BY operator
                ORDER BY cnt DESC
            """)
            rows = c.fetchall()
            print("\n【1】正常数据操作员分布:")
            for r in rows:
                print(f"  {r['operator']}: {r['cnt']}条, 共{r['total_qty']}件")

            # 2. 非测试数据的订单分布
            c.execute("""
                SELECT order_no, COUNT(*) as cnt, SUM(quantity) as total_qty
                FROM process_sub_steps
                WHERE operator NOT LIKE 'stress-%'
                  AND operator NOT LIKE '8008-stress-%'
                GROUP BY order_no
                ORDER BY cnt DESC
            """)
            rows = c.fetchall()
            print(f"\n【2】正常数据订单分布 ({len(rows)}个订单):")
            for r in rows:
                print(f"  {r['order_no']}: {r['cnt']}条, 共{r['total_qty']}件")

            # 3. ORD-20260416-0001/入库 正常报工数据
            c.execute("""
                SELECT operator, SUM(quantity) as total, COUNT(*) as cnt
                FROM process_sub_steps
                WHERE order_no = 'ORD-20260416-0001'
                  AND step_name = '入库'
                  AND operator NOT LIKE 'stress-%'
                  AND operator NOT LIKE '8008-stress-%'
                GROUP BY operator
                ORDER BY total DESC
            """)
            rows = c.fetchall()
            print(f"\n【3】ORD-20260416-0001/入库 正常报工({len(rows)}个操作员):")
            total_normal = 0
            for r in rows:
                total_normal += r['total']
                print(f"  {r['operator']}: {r['total']}件 x {r['cnt']}次")
            print(f"  正常报工总数量: {total_normal}")

            # 4. process_records 当前值
            c.execute("""
                SELECT completed_qty
                FROM process_records
                WHERE order_no = 'ORD-20260416-0001'
                  AND process_name = '入库'
            """)
            row = c.fetchone()
            if row:
                print(f"\n【4】process_records 当前 completed_qty: {row['completed_qty']}")
                print(f"  测试数据贡献: 27373")
                print(f"  正常数据贡献: {total_normal}")
                print(f"  修正后应为: {total_normal}")
            else:
                print(f"\n【4】process_records 中无此记录")

    finally:
        conn.close()


def check_8008_pattern():
    """检查是否有 8008-stress- 模式的操作员"""
    conn = get_conn('steel_belt')
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT operator, COUNT(*) as cnt
                FROM process_sub_steps
                WHERE operator LIKE '8008-stress-%'
                   OR operator LIKE '8008-%'
                   OR operator LIKE 'test-%'
                GROUP BY operator
                ORDER BY cnt DESC
            """)
            rows = c.fetchall()
            print(f"\n【5】其他测试操作员模式:")
            if rows:
                for r in rows:
                    print(f"  {r['operator']}: {r['cnt']}条")
            else:
                print(f"  无 '8008-stress-', '8008-', 'test-' 模式的数据")
    finally:
        conn.close()


def analyze_report_queue():
    """修复 collation 问题的 queue 分析"""
    conn = get_conn('container_center')
    try:
        with conn.cursor() as c:
            # 直接查所有 report_queue 详情
            c.execute("""
                SELECT id, order_no, step_name, status, error_msg, retry_count, enqueued_at
                FROM report_queue
                ORDER BY enqueued_at DESC
                LIMIT 20
            """)
            rows = c.fetchall()
            print(f"\n【6】report_queue 最近记录:")
            for r in rows:
                status_mark = '✅' if r['status'] == 'completed' else '❌'
                err = f" | 错误: {r['error_msg'][:50]}" if r['error_msg'] else ''
                print(f"  {status_mark} #{r['id']} {r['order_no']}/{r['step_name']} [{r['status']}] 重试={r['retry_count']}{err}")

            # 失败的记录
            c.execute("""
                SELECT id, order_no, step_name, error_msg, enqueued_at
                FROM report_queue
                WHERE status = 'failed'
            """)
            rows = c.fetchall()
            print(f"\n【7】report_queue 失败记录:")
            for r in rows:
                print(f"  ❌ #{r['id']} {r['order_no']}/{r['step_name']}: {r['error_msg'][:100]}")

    finally:
        conn.close()


def main():
    print("=" * 60)
    print("测试数据补充分析")
    print("=" * 60)
    analyze_normal_data()
    check_8008_pattern()
    analyze_report_queue()
    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
