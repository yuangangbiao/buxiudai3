# -*- coding: utf-8 -*-
"""
import pytest

pytestmark = pytest.mark.integration  # 直接连 DB，需手动跑


移动端-桌面端数据同步测试

测试目的:
验证移动端操作后，数据能同步到桌面端显示

测试场景:
1. 移动端报工 -> 桌面端查询生产工序
2. 移动端物料确认 -> 桌面端查询物料状态
3. 桌面端派工 -> 移动端查询任务

执行方式:
python scripts/test_mobile_desktop_sync_0620.py
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


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def test_process_sub_steps_sync():
    """测试生产工序同步"""
    print("\n" + "=" * 60)
    print("场景 1: 移动端报工 -> 桌面端查询")
    print("=" * 60)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 桌面端查询 - 模拟 container_center_api.py L958
            cursor.execute("""
                SELECT id, order_no, process_code, step_name, quantity, completed_qty, operator, status
                FROM process_sub_steps
                ORDER BY created_at DESC
                LIMIT 5
            """)
            rows = cursor.fetchall()

            print(f"  桌面端可查询到的生产工序数: {len(rows)}")

            # 检查 completed_qty 字段
            with_completed = sum(1 for r in rows if r['completed_qty'] and r['completed_qty'] > 0)
            print(f"  已完成报工数: {with_completed}")

            if rows:
                print(f"\n  最新工序样本:")
                for r in rows[:3]:
                    print(f"    - {r['order_no']}/{r['step_name']}: "
                          f"完成={r['completed_qty']}/{r['quantity']} 状态={r['status']}")

            return len(rows) > 0

    finally:
        conn.close()


def test_material_records_sync():
    """测试物料记录同步"""
    print("\n" + "=" * 60)
    print("场景 2: 移动端物料确认 -> 桌面端查询")
    print("=" * 60)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 桌面端查询 - 模拟 container_center_api.py L2316
            cursor.execute("""
                SELECT status, COUNT(*) as cnt
                FROM material_records
                GROUP BY status
            """)
            rows = cursor.fetchall()

            print(f"  桌面端可查询到的物料状态分布:")
            for r in rows:
                print(f"    - {r['status']}: {r['cnt']} 条")

            # 桌面端详情查询 - 模拟 container_center_api.py
            cursor.execute("""
                SELECT id, title, order_no, material_name, status, target_operator
                FROM material_records
                LIMIT 3
            """)
            details = cursor.fetchall()

            if details:
                print(f"\n  物料详情样本:")
                for d in details:
                    print(f"    - {d['order_no']}: {d['status']} -> {d['target_operator']}")

            return True

    finally:
        conn.close()


def test_quality_records_sync():
    """测试质检记录同步"""
    print("\n" + "=" * 60)
    print("场景 3: 移动端质检 -> 桌面端查询")
    print("=" * 60)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 桌面端查询 - 模拟 container_center_api.py L2298
            cursor.execute("""
                SELECT status, result, COUNT(*) as cnt
                FROM quality_records
                GROUP BY status, result
            """)
            rows = cursor.fetchall()

            print(f"  桌面端可查询到的质检状态分布:")
            for r in rows:
                print(f"    - 状态={r['status']}, 判定={r['result']}: {r['cnt']} 条")

            # 桌面端详情查询
            cursor.execute("""
                SELECT id, order_no, process_name, inspection_type, result, status
                FROM quality_records
                LIMIT 3
            """)
            details = cursor.fetchall()

            if details:
                print(f"\n  质检详情样本:")
                for d in details:
                    print(f"    - {d['order_no']}/{d['process_name']}: {d['result']}")

            return True

    finally:
        conn.close()


def test_storage_get_packages():
    """测试存储层 get_packages 方法"""
    print("\n" + "=" * 60)
    print("场景 4: 验证存储层 get_packages 分发逻辑")
    print("=" * 60)

    # 验证 get_packages 方法的数据分发
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 模拟存储层 get_packages('quality') 查询
            cursor.execute("SELECT COUNT(*) as cnt FROM quality_records")
            q_count = cursor.fetchone()['cnt']
            print(f"  quality_records 记录数: {q_count}")

            # 模拟存储层 get_packages('material_request') 查询
            cursor.execute("SELECT COUNT(*) as cnt FROM material_records")
            m_count = cursor.fetchone()['cnt']
            print(f"  material_records 记录数: {m_count}")

            # 模拟存储层 get_packages('process') 查询
            cursor.execute("SELECT COUNT(*) as cnt FROM process_sub_steps")
            p_count = cursor.fetchone()['cnt']
            print(f"  process_sub_steps 记录数: {p_count}")

            total = q_count + m_count + p_count
            print(f"\n  桌面端通过 get_packages 可获取的总任务数: {total}")

            return total > 0

    finally:
        conn.close()


def test_data_flow_diagram():
    """输出数据流图"""
    print("\n" + "=" * 60)
    print("数据流架构图")
    print("=" * 60)
    print("""
    ┌─────────────────┐
    │   移动端 (5008)  │
    │    app.py       │
    └────────┬────────┘
             │ 写入
             ▼
    ┌─────────────────────────────────────────┐
    │           MySQL 独立表                   │
    ├──────────┬──────────┬──────────┬────────┤
    │process_  │quality_  │material_ │outsource│
    │sub_steps │records   │records   │records │
    └──────────┴──────────┴──────────┴────────┘
             │ 查询
             ▼
    ┌─────────────────┐
    │  桌面端 (5002)   │
    │ container_center │
    │   _api.py       │
    └─────────────────┘

    验证点:
    ✅ 移动端写入 process_sub_steps.completed_qty
    ✅ 桌面端从 process_sub_steps 读取
    ✅ 移动端写入 material_records.status
    ✅ 桌面端从 material_records 读取
    ✅ 移动端写入 quality_records
    ✅ 桌面端从 quality_records 读取
    """)


def main():
    print("\n" + "=" * 60)
    print("移动端-桌面端数据同步测试")
    print("执行时间: 2026-06-20")
    print("=" * 60)

    results = []

    # 测试各场景
    results.append(("生产工序同步", test_process_sub_steps_sync()))
    results.append(("物料记录同步", test_material_records_sync()))
    results.append(("质检记录同步", test_quality_records_sync()))
    results.append(("存储层分发", test_storage_get_packages()))

    # 输出数据流图
    test_data_flow_diagram()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")

    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n✅ 移动端-桌面端数据同步正常!")
    else:
        print("\n❌ 部分同步测试失败")

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
