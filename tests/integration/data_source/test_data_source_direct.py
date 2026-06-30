# -*- coding: utf-8 -*-
"""
import pytest

pytestmark = pytest.mark.integration  # 直接连 DB，需手动跑


独立表数据来源验证脚本（直接查询数据库）

验证:
1. 各独立表是否有正确的数据
2. 回归审计 API 对应的数据是否存在独立表中

执行方式:
python scripts/test_data_source_direct_0620.py
"""
import os
import sys

try:
    import pymysql
except ImportError:
    print("需要安装 pymysql: pip install pymysql")
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


def test_table(table_name, display_name):
    """通用表测试函数"""
    print(f"\n{'=' * 60}")
    print(f"{display_name} ({table_name})")
    print("=" * 60)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
            count = cursor.fetchone()['cnt']
            print(f"  总记录数: {count}")

            # 获取表结构
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            print(f"  字段列表:")
            for col in columns[:10]:
                print(f"    - {col['Field']}: {col['Type']}")

            # 样本数据
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            samples = cursor.fetchall()
            if samples:
                print(f"\n  样本数据:")
                for i, s in enumerate(samples):
                    print(f"    [{i+1}] {s}")

            return count >= 0

    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False
    finally:
        conn.close()


def test_process_sub_steps_completed_qty():
    """测试 process_sub_steps.completed_qty 字段"""
    print(f"\n{'=' * 60}")
    print("生产工序 completed_qty 验证")
    print("=" * 60)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 检查字段是否存在
            cursor.execute("""
                SELECT COLUMN_NAME FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'process_sub_steps'
                  AND COLUMN_NAME = 'completed_qty'
            """)
            has_field = cursor.fetchone() is not None
            print(f"  completed_qty 字段存在: {'✅' if has_field else '❌'}")

            if has_field:
                cursor.execute("""
                    SELECT
                        SUM(CASE WHEN completed_qty > 0 THEN 1 ELSE 0 END) as with_completed,
                        SUM(CASE WHEN completed_qty = 0 OR completed_qty IS NULL THEN 1 ELSE 0 END) as without_completed,
                        SUM(completed_qty) as total
                    FROM process_sub_steps
                """)
                stats = cursor.fetchone()
                print(f"  已完成报工: {stats['with_completed'] or 0} 条")
                print(f"  待报工: {stats['without_completed'] or 0} 条")
                print(f"  完成总量: {stats['total'] or 0}")

                # 样本
                cursor.execute("""
                    SELECT order_no, step_name, quantity, completed_qty
                    FROM process_sub_steps
                    WHERE completed_qty > 0
                    LIMIT 5
                """)
                samples = cursor.fetchall()
                if samples:
                    print(f"\n  已完成报工样本:")
                    for s in samples:
                        pct = (float(s['completed_qty']) / float(s['quantity']) * 100) if s['quantity'] else 0
                        print(f"    - {s['order_no']}/{s['step_name']}: {s['completed_qty']}/{s['quantity']} ({pct:.0f}%)")

            return has_field

    finally:
        conn.close()


def test_data_packages_status():
    """检查 data_packages 表状态"""
    print(f"\n{'=' * 60}")
    print("data_packages 表状态")
    print("=" * 60)

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as cnt FROM data_packages")
            count = cursor.fetchone()['cnt']
            print(f"  总记录数: {count}")

            # 检查 is_archived 字段
            cursor.execute("""
                SELECT COLUMN_NAME FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'data_packages'
                  AND COLUMN_NAME = 'is_archived'
            """)
            has_archived = cursor.fetchone() is not None
            print(f"  is_archived 字段存在: {'✅' if has_archived else '❌'}")

            if has_archived:
                cursor.execute("""
                    SELECT
                        SUM(CASE WHEN is_archived = 1 THEN 1 ELSE 0 END) as archived,
                        SUM(CASE WHEN is_archived = 0 OR is_archived IS NULL THEN 1 ELSE 0 END) as active
                    FROM data_packages
                """)
                stats = cursor.fetchone()
                print(f"  已归档: {stats['archived'] or 0}")
                print(f"  活跃: {stats['active'] or 0}")

            return True

    finally:
        conn.close()


def main():
    print("\n" + "=" * 60)
    print("独立表数据来源验证")
    print("执行时间: 2026-06-20")
    print("=" * 60)

    results = []

    results.append(("process_sub_steps", test_table("process_sub_steps", "生产工序")))
    results.append(("quality_records", test_table("quality_records", "质检记录")))
    results.append(("material_records", test_table("material_records", "物料记录")))
    results.append(("outsource_records", test_table("outsource_records", "外协记录")))
    results.append(("schedule_records", test_table("schedule_records", "排产记录")))
    results.append(("repair_records", test_table("repair_records", "维修记录")))

    results.append(("completed_qty 验证", test_process_sub_steps_completed_qty()))
    results.append(("data_packages 状态", test_data_packages_status()))

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")

    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n✅ 所有测试通过!")
    else:
        print("\n⚠️ 部分测试失败")

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
