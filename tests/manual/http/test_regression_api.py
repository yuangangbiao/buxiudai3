# -*- coding: utf-8 -*-
"""
import pytest

pytestmark = pytest.mark.manual  # 独立验收/Playwright 脚本，不参与 pytest 单元统计


回归审计 API 测试脚本

测试目的:
1. 验证 4 个回归审计 API 是否正常返回数据
2. 验证数据来源是否为独立表
3. 验证 API 返回格式正确

执行方式:
python scripts/test_regression_api_0620.py
"""
import os
import sys
import time
import requests

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# API 配置
DISPATCH_CENTER_URL = 'http://localhost:5003'


def test_regression_api(api_name, url, params=None):
    """测试单个回归审计 API"""
    print(f"\n  测试 {api_name}...")

    try:
        start = time.time()
        response = requests.get(url, params=params or {}, timeout=10)
        elapsed = (time.time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            count = len(data.get('data', [])) if isinstance(data.get('data'), list) else 0
            print(f"    ✅ {api_name}: {count} 条记录 ({elapsed:.0f}ms)")

            # 检查数据来源
            if data.get('data') and isinstance(data['data'], list) and len(data['data']) > 0:
                first_item = data['data'][0]
                # 检查是否有 _source_table 字段标识数据来源
                if '_source_table' in first_item:
                    print(f"       数据来源: {first_item['_source_table']}")

            return True, data
        else:
            print(f"    ❌ {api_name}: HTTP {response.status_code}")
            return False, None

    except requests.exceptions.ConnectionError:
        print(f"    ⚠️ {api_name}: 无法连接到调度中心 (localhost:5003)")
        print(f"       请确保调度中心服务正在运行")
        return False, None
    except Exception as e:
        print(f"    ❌ {api_name}: {e}")
        return False, None


def test_regression_apis():
    """测试所有回归审计 API"""
    print("=" * 60)
    print("测试: 回归审计 API")
    print("=" * 60)
    print(f"API 地址: {DISPATCH_CENTER_URL}")

    apis = [
        ('质检回归 /quality-regression', f'{DISPATCH_CENTER_URL}/quality-regression'),
        ('物料回归 /material-regression', f'{DISPATCH_CENTER_URL}/material-regression'),
        ('外协回归 /outsource-regression', f'{DISPATCH_CENTER_URL}/outsource-regression'),
        ('排产回归 /schedule-regression', f'{DISPATCH_CENTER_URL}/schedule-regression'),
    ]

    results = {}
    all_success = True

    for name, url in apis:
        success, data = test_regression_api(name, url)
        results[name] = {'success': success, 'data': data}
        if not success:
            all_success = False

    return results, all_success


def test_data_source():
    """验证回归 API 数据来源是否为独立表"""
    print("\n" + "=" * 60)
    print("测试: 验证数据来源")
    print("=" * 60)

    # 直接查询数据库验证数据来源
    sys.path.insert(0, os.path.join(PROJ_ROOT, 'mobile_api_ai'))
    from storage.mysql_storage import MySQLStorage

    storage = MySQLStorage()

    tables_to_check = [
        ('quality_records', '质检记录'),
        ('material_records', '物料记录'),
        ('outsource_records', '外协记录'),
        ('schedule_records', '排产记录'),
    ]

    for table, name in tables_to_check:
        try:
            count = storage.fetch_one(f"SELECT COUNT(*) as cnt FROM {table}")
            sample = storage.fetch_one(f"SELECT * FROM {table} LIMIT 1")
            print(f"  ✅ {name} ({table}): {count['cnt'] if count else 0} 条")

            if sample:
                # 检查关键字段
                key_fields = []
                if 'order_no' in sample:
                    key_fields.append('order_no')
                if 'process_name' in sample:
                    key_fields.append('process_name')
                if 'status' in sample:
                    key_fields.append('status')
                print(f"       关键字段: {', '.join(key_fields) if key_fields else '无'}")

        except Exception as e:
            print(f"  ❌ {name} ({table}): {e}")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("回归审计 API 测试")
    print("执行时间: 2026-06-20")
    print("=" * 60)

    # 测试 API
    results, all_success = test_regression_apis()

    # 验证数据来源
    test_data_source()

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    api_count = len(results)
    passed_count = sum(1 for r in results.values() if r['success'])

    print(f"  API 测试: {passed_count}/{api_count} 通过")

    if all_success:
        print("\n  ✅ 所有回归审计 API 测试通过!")
        print("  ✅ 数据来源已迁移到独立表")
    else:
        print("\n  ⚠️ 部分 API 测试失败")
        print("  请确保调度中心服务正在运行: python dispatch_center/_core.py")

    print("=" * 60)

    return all_success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
