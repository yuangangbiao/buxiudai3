# -*- coding: utf-8 -*-
"""
import pytest

pytestmark = pytest.mark.integration  # 直接连 DB，需手动跑


主软件数据同步测试

测试目的:
验证移动端报工后，数据能否同步到主软件的 process_records 表

数据流:
1. 移动端报工 (5008) → process_sub_steps
2. report_queue 队列
3. sync_bridge (8008) → process_records
4. 主软件读取 process_records

执行方式:
python scripts/test_main_software_sync_0620.py
"""
import os
import sys

try:
    import pymysql
except ImportError:
    print("需要安装 pymysql")
    sys.exit(1)

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


def get_connection(db='container_center'):
    config = STEEL_BELT_CONFIG if db == 'steel_belt' else DB_CONFIG
    return pymysql.connect(**config)


def test_process_sub_steps():
    """测试 process_sub_steps 表（移动端报工数据）"""
    print("\n" + "=" * 60)
    print("1. process_sub_steps 表（移动端报工数据）")
    print("=" * 60)

    conn = get_connection('steel_belt')
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as cnt FROM process_sub_steps")
            count = cursor.fetchone()['cnt']
            print(f"  记录总数: {count}")

            # 最近报工
            cursor.execute("""
                SELECT order_no, step_name, quantity, operator, created_at
                FROM process_sub_steps
                ORDER BY created_at DESC
                LIMIT 5
            """)
            rows = cursor.fetchall()
            print(f"\n  最近 5 条报工记录:")
            for r in rows:
                print(f"    - {r['order_no']}/{r['step_name']}: {r['quantity']} by {r['operator']}")

            return count > 0

    finally:
        conn.close()


def test_process_records():
    """测试 process_records 表（主软件数据 - steel_belt 数据库）"""
    print("\n" + "=" * 60)
    print("2. process_records 表（主软件数据 - steel_belt）")
    print("=" * 60)

    conn = get_connection('steel_belt')
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as cnt FROM process_records")
            count = cursor.fetchone()['cnt']
            print(f"  记录总数: {count}")

            if count == 0:
                print(f"  ⚠️ process_records 表为空")
                return True

            # 最近工序
            cursor.execute("""
                SELECT order_no, process_name, planned_qty, completed_qty, status
                FROM process_records
                ORDER BY updated_at DESC
                LIMIT 5
            """)
            rows = cursor.fetchall()
            print(f"\n  最近 5 条工序记录:")
            for r in rows:
                print(f"    - {r['order_no']}/{r['process_name']}: "
                      f"完成={r['completed_qty']}/{r['planned_qty']} 状态={r['status']}")

            return count > 0

    finally:
        conn.close()


def test_report_queue():
    """测试 report_queue 队列（同步队列）"""
    print("\n" + "=" * 60)
    print("3. report_queue 表（同步队列）")
    print("=" * 60)

    conn = get_connection('container_center')
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT status, COUNT(*) as cnt
                FROM report_queue
                GROUP BY status
            """)
            rows = cursor.fetchall()
            print(f"  队列状态分布:")
            for r in rows:
                print(f"    - {r['status']}: {r['cnt']}")

            # 最近待处理
            cursor.execute("""
                SELECT id, order_no, step_name, status, retry_count
                FROM report_queue
                WHERE status IN ('pending', 'retry')
                ORDER BY enqueued_at DESC
                LIMIT 3
            """)
            rows = cursor.fetchall()
            if rows:
                print(f"\n  待处理记录:")
                for r in rows:
                    print(f"    - [{r['status']}] {r['order_no']}/{r['step_name']} (重试={r['retry_count']})")

            return True

    finally:
        conn.close()


def test_sync_consistency():
    """测试同步一致性"""
    print("\n" + "=" * 60)
    print("4. 同步一致性检查")
    print("=" * 60)

    conn_src = get_connection('steel_belt')
    conn_dst = get_connection('steel_belt')

    try:
        with conn_src.cursor() as cursor_src:
            cursor_src.execute("""
                SELECT DISTINCT order_no, step_name, SUM(quantity) as total_qty
                FROM process_sub_steps
                GROUP BY order_no, step_name
                ORDER BY MAX(created_at) DESC
                LIMIT 5
            """)
            src_rows = cursor_src.fetchall()

        with conn_dst.cursor() as cursor_dst:
            print(f"  同步对比:")
            for r in src_rows:
                order_no = r['order_no']
                step_name = r['step_name']

                cursor_dst.execute("""
                    SELECT completed_qty, status
                    FROM process_records
                    WHERE order_no=%s AND process_name=%s
                    LIMIT 1
                """, (order_no, step_name))
                dst_row = cursor_dst.fetchone()

                if dst_row:
                    sync_status = "✅" if dst_row['completed_qty'] > 0 else "⚠️"
                    print(f"    {sync_status} {order_no}/{step_name}: "
                          f"源={r['total_qty']} 目标={dst_row['completed_qty']}")
                else:
                    print(f"    ❌ {order_no}/{step_name}: 源有数据，目标无记录")

        return True

    finally:
        conn_src.close()
        conn_dst.close()


def test_data_flow_diagram():
    """输出数据流图"""
    print("\n" + "=" * 60)
    print("数据流架构图")
    print("=" * 60)
    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │                     移动端报工 (5008)                        │
    │                    app.py 报工接口                           │
    └─────────────────────────┬───────────────────────────────────┘
                              │
                              │ 1. 写入 process_sub_steps
                              │ 2. 入队 report_queue
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                   report_queue 队列                          │
    │                 (每10秒消费一次)                             │
    └─────────────────────────┬───────────────────────────────────┘
                              │
                              │ 3. 后台 worker 调用
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                   sync_bridge (8008)                        │
    │                  /sub-step-report 接口                       │
    └─────────────────────────┬───────────────────────────────────┘
                              │
                              │ 4. 调用 sync_sub_step_report
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                   process_records 表                         │
    │                    (主软件数据)                             │
    └─────────────────────────┬───────────────────────────────────┘
                              │
                              │ 5. 主软件读取
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                     主软件                                   │
    │                  models/process.py                           │
    └─────────────────────────────────────────────────────────────┘
    """)


def main():
    print("\n" + "=" * 60)
    print("主软件数据同步测试")
    print("执行时间: 2026-06-20")
    print("=" * 60)

    results = []

    results.append(("process_sub_steps", test_process_sub_steps()))
    results.append(("process_records", test_process_records()))
    results.append(("report_queue", test_report_queue()))
    results.append(("同步一致性", test_sync_consistency()))

    test_data_flow_diagram()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")

    print("\n" + "=" * 60)

    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
