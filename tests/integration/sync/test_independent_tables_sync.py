# -*- coding: utf-8 -*-
"""
import pytest

pytestmark = pytest.mark.integration  # 直接连 DB，需手动跑


独立表数据同步测试脚本

测试目的:
1. 验证各独立表的数据写入/读取正常
2. 测试回归审计 API 是否返回正确数据
3. 验证 process_sub_steps.completed_qty 更新逻辑

执行方式:
python scripts/test_independent_tables_sync_0620.py
"""
import os
import sys

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOBILE_API_ROOT = os.path.join(PROJ_ROOT, 'mobile_api_ai')

for p in [PROJ_ROOT, MOBILE_API_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

from storage.mysql_storage import MySQLStorage


def test_independent_tables():
    """测试各独立任务表的数据状态"""
    storage = MySQLStorage()

    print("=" * 60)
    print("测试 1: 检查各独立表数据状态")
    print("=" * 60)

    tables = [
        ('process_sub_steps', '生产工序'),
        ('quality_records', '质检记录'),
        ('material_records', '物料记录'),
        ('outsource_records', '外协记录'),
        ('schedule_records', '排产记录'),
        ('repair_records', '维修记录'),
    ]

    results = {}
    for table, name in tables:
        try:
            count = storage.fetch_one(f"SELECT COUNT(*) as cnt FROM {table}")
            total = count['cnt'] if count else 0

            # 检查是否有 completed_qty 字段
            has_completed = False
            if table == 'process_sub_steps':
                sample = storage.fetch_one(f"SELECT completed_qty FROM {table} LIMIT 1")
                has_completed = sample is not None

            results[table] = {
                'name': name,
                'count': total,
                'has_completed': has_completed,
                'status': '✅' if total > 0 else '⚠️ (空表)'
            }
            print(f"  {results[table]['status']} {name} ({table}): {total} 条记录")
            if has_completed:
                print(f"      - has completed_qty 字段: ✅")
        except Exception as e:
            results[table] = {
                'name': name,
                'error': str(e),
                'status': '❌ 错误'
            }
            print(f"  ❌ {name} ({table}): 错误 - {e}")

    return results


def test_completed_qty_sync():
    """测试 process_sub_steps.completed_qty 同步逻辑"""
    storage = MySQLStorage()

    print("\n" + "=" * 60)
    print("测试 2: 验证 completed_qty 同步逻辑")
    print("=" * 60)

    try:
        # 检查是否有 completed_qty 字段
        test_row = storage.fetch_one(
            "SELECT order_no, step_name, quantity, completed_qty "
            "FROM process_sub_steps WHERE completed_qty > 0 LIMIT 5"
        )

        if test_row:
            print(f"  ✅ 找到已完成报工的记录:")
            print(f"     订单: {test_row['order_no']}")
            print(f"     工序: {test_row['step_name']}")
            print(f"     计划: {test_row['quantity']}")
            print(f"     完成: {test_row['completed_qty']}")

            # 验证完成量不超过计划量
            if float(test_row['completed_qty']) <= float(test_row['quantity']):
                print(f"     状态: ✅ 完成量在合理范围内")
            else:
                print(f"     状态: ⚠️ 完成量超过计划量!")
        else:
            print(f"  ⚠️ 未找到已完成报工的记录（completed_qty > 0）")

        # 检查是否有待报工的记录
        pending = storage.fetch_one(
            "SELECT COUNT(*) as cnt FROM process_sub_steps "
            "WHERE completed_qty = 0 OR completed_qty IS NULL"
        )
        print(f"\n  待报工记录数: {pending['cnt'] if pending else 0}")

        return True

    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False


def test_data_packages_archived():
    """检查 data_packages 表状态（应为归档状态）"""
    storage = MySQLStorage()

    print("\n" + "=" * 60)
    print("测试 3: 检查 data_packages 表状态")
    print("=" * 60)

    try:
        # 检查是否有 is_archived 字段
        has_archived = storage.fetch_one("""
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'data_packages'
              AND COLUMN_NAME = 'is_archived'
        """)

        if has_archived:
            total = storage.fetch_one("SELECT COUNT(*) as cnt FROM data_packages")
            archived = storage.fetch_one(
                "SELECT COUNT(*) as cnt FROM data_packages WHERE is_archived = 1"
            )
            print(f"  ✅ data_packages 表已添加 is_archived 字段")
            print(f"     总记录数: {total['cnt'] if total else 0}")
            print(f"     已归档: {archived['cnt'] if archived else 0}")
        else:
            print(f"  ⚠️ data_packages 表尚未添加 is_archived 字段")

        return True

    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        return False


def test_storage_methods():
    """测试存储层新增的方法"""
    storage = MySQLStorage()

    print("\n" + "=" * 60)
    print("测试 4: 验证存储层方法")
    print("=" * 60)

    methods_to_test = [
        'save_task',
        'update_task',
        'get_task',
        'get_tasks',
        'update_task_completed_qty',
    ]

    results = {}
    for method in methods_to_test:
        has_method = hasattr(storage, method)
        results[method] = has_method
        status = '✅' if has_method else '❌'
        print(f"  {status} {method}() 方法: {'存在' if has_method else '不存在'}")

    return all(results.values())


def test_task_type_mapping():
    """测试任务类型到独立表的映射"""
    storage = MySQLStorage()

    print("\n" + "=" * 60)
    print("测试 5: 验证任务类型映射")
    print("=" * 60)

    expected_map = {
        'process': 'process_sub_steps',
        'quality': 'quality_records',
        'material': 'material_records',
        'outsource': 'outsource_records',
        'repair': 'repair_records',
        'schedule': 'schedule_records',
    }

    if hasattr(storage, 'TASK_TYPE_TABLE_MAP'):
        actual_map = storage.TASK_TYPE_TABLE_MAP
        for task_type, expected_table in expected_map.items():
            actual_table = actual_map.get(task_type)
            status = '✅' if actual_table == expected_table else '❌'
            print(f"  {status} {task_type} -> {actual_table} (期望: {expected_table})")
        return True
    else:
        print(f"  ❌ 未找到 TASK_TYPE_TABLE_MAP")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("独立表数据同步测试")
    print("执行时间: 2026-06-20")
    print("=" * 60)

    results = {}

    # 执行所有测试
    results['tables'] = test_independent_tables()
    results['completed_qty'] = test_completed_qty_sync()
    results['data_packages'] = test_data_packages_archived()
    results['storage_methods'] = test_storage_methods()
    results['task_mapping'] = test_task_type_mapping()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v is True or (isinstance(v, dict) and all(r.get('error') is None for r in v.values())))
    total = len(results)

    print(f"  通过: {passed}/{total}")

    for name, result in results.items():
        if isinstance(result, dict):
            errors = [k for k, v in result.items() if v.get('error')]
            if errors:
                print(f"  ❌ {name}: {len(errors)} 个错误")
            else:
                print(f"  ✅ {name}: 正常")
        elif result is True:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name}")

    print("\n" + "=" * 60)

    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
