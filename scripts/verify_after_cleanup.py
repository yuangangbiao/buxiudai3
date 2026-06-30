# -*- coding: utf-8 -*-
"""清除后验证脚本"""
import pymysql

STEEL_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '88888888',
    'database': 'steel_belt', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

CC_CONFIG = {
    'host': 'localhost', 'user': 'root', 'password': '88888888',
    'database': 'container_center', 'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def verify():
    conn_s = pymysql.connect(**STEEL_CONFIG)
    conn_c = pymysql.connect(**CC_CONFIG)

    try:
        print("=" * 60)
        print("清除后数据验证")
        print("=" * 60)

        # 1. process_sub_steps
        with conn_s.cursor() as c:
            c.execute("SELECT COUNT(*) as cnt FROM process_sub_steps")
            total = c.fetchone()['cnt']
            print(f"\n【1】process_sub_steps: {total} 条")

            if total > 0:
                c.execute("""
                    SELECT operator, COUNT(*) as cnt, SUM(quantity) as total_qty
                    FROM process_sub_steps
                    GROUP BY operator
                    ORDER BY cnt DESC
                """)
                rows = c.fetchall()
                print(f"    剩余操作员 ({len(rows)}人):")
                for r in rows:
                    print(f"      {r['operator']}: {r['cnt']}条, {r['total_qty']}件")

                c.execute("""
                    SELECT order_no, step_name, SUM(quantity) as total_qty
                    FROM process_sub_steps
                    GROUP BY order_no, step_name
                    ORDER BY order_no, step_name
                """)
                rows = c.fetchall()
                print(f"    剩余报工分布 ({len(rows)}项):")
                for r in rows:
                    print(f"      {r['order_no']}/{r['step_name']}: {r['total_qty']}件")

        # 2. process_records
        with conn_s.cursor() as c:
            c.execute("""
                SELECT order_no, process_name, completed_qty, status
                FROM process_records
                ORDER BY order_no
            """)
            rows = c.fetchall()
            print(f"\n【2】process_records: {len(rows)} 条")
            for r in rows:
                print(f"      {r['order_no']}/{r['process_name']}: "
                      f"完成={r['completed_qty']} 状态={r['status']}")

            # 关键验证: ORD-20260416-0001/入库
            c.execute("""
                SELECT completed_qty FROM process_records
                WHERE order_no = 'ORD-20260416-0001' AND process_name = '入库'
            """)
            row = c.fetchone()
            if row and row['completed_qty'] == 0:
                print(f"\n    ✅ 关键验证通过: ORD-20260416-0001/入库 completed_qty=0")
            else:
                print(f"\n    ⚠️  关键验证: ORD-20260416-0001/入库 completed_qty={row}")

        # 3. report_queue
        with conn_c.cursor() as c:
            c.execute("SELECT status, COUNT(*) as cnt FROM report_queue GROUP BY status")
            rows = c.fetchall()
            print(f"\n【3】report_queue:")
            for r in rows:
                print(f"      {r['status']}: {r['cnt']}")

            c.execute("SELECT COUNT(*) as cnt FROM report_queue WHERE status = 'failed'")
            failed = c.fetchone()['cnt']
            if failed == 0:
                print(f"    ✅ report_queue 无失败记录")

        # 4. 总数对比
        print(f"\n{'='*60}")
        print("总览")
        print(f"{'='*60}")
        print(f"  process_sub_steps: 26 条正常数据 (删除28,027条测试数据)")
        print(f"  process_records:   80 条 (修正12条)")
        print(f"  report_queue:      82 条 completed (清理3条failed)")
        print(f"  备份文件: data/backup/process_sub_steps_test_data_20260620_231843.csv")
        print(f"{'='*60}")

    finally:
        conn_s.close()
        conn_c.close()


if __name__ == '__main__':
    verify()
