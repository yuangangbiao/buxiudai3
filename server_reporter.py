#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器测试报告生成器
"""
import requests
import time
from pathlib import Path

PROJECT_ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

def test_server():
    results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'tests': [],
        'summary': {'passed': 0, 'failed': 0}
    }

    print("="*60)
    print("手机报工服务器 (5008) 测试报告")
    print("="*60)
    print(f"测试时间: {results['timestamp']}\n")

    # 测试 1: 首页访问
    print("[测试 1] 首页访问...")
    try:
        resp = requests.get("http://localhost:5008/", timeout=5)
        test_result = {
            'name': '首页访问',
            'status': 'PASS' if resp.status_code == 200 else 'FAIL',
            'code': resp.status_code,
            'length': len(resp.text)
        }
        results['tests'].append(test_result)
        results['summary']['passed' if resp.status_code == 200 else 'failed'] += 1
        print(f"  状态码: {resp.status_code}, 内容长度: {len(resp.text)}")
        print(f"  {'✅ PASS' if resp.status_code == 200 else '❌ FAIL'}")
    except Exception as e:
        test_result = {'name': '首页访问', 'status': 'FAIL', 'error': str(e)}
        results['tests'].append(test_result)
        results['summary']['failed'] += 1
        print(f"  ❌ FAIL: {e}")

    # 测试 2: API 健康检查
    print("\n[测试 2] API 健康检查...")
    try:
        resp = requests.get("http://localhost:5008/api/health", timeout=5)
        test_result = {
            'name': 'API健康检查',
            'status': 'PASS' if resp.status_code == 200 else 'FAIL',
            'code': resp.status_code,
            'response': resp.text[:200]
        }
        results['tests'].append(test_result)
        results['summary']['passed' if resp.status_code == 200 else 'failed'] += 1
        print(f"  状态码: {resp.status_code}")
        print(f"  响应: {resp.text[:100]}")
        print(f"  {'✅ PASS' if resp.status_code == 200 else '❌ FAIL'}")
    except Exception as e:
        test_result = {'name': 'API健康检查', 'status': 'FAIL', 'error': str(e)}
        results['tests'].append(test_result)
        results['summary']['failed'] += 1
        print(f"  ❌ FAIL: {e}")

    # 测试 3: 订单 API
    print("\n[测试 3] 订单列表 API...")
    try:
        resp = requests.get("http://localhost:5008/api/orders", timeout=5)
        test_result = {
            'name': '订单列表API',
            'status': 'PASS' if resp.status_code == 200 else 'FAIL',
            'code': resp.status_code,
            'length': len(resp.text)
        }
        results['tests'].append(test_result)
        results['summary']['passed' if resp.status_code == 200 else 'failed'] += 1
        print(f"  状态码: {resp.status_code}")
        print(f"  {'✅ PASS' if resp.status_code == 200 else '❌ FAIL'}")
    except Exception as e:
        test_result = {'name': '订单列表API', 'status': 'FAIL', 'error': str(e)}
        results['tests'].append(test_result)
        results['summary']['failed'] += 1
        print(f"  ❌ FAIL: {e}")

    # 测试 4: 页面内容分析
    print("\n[测试 4] 页面内容分析...")
    try:
        resp = requests.get("http://localhost:5008/", timeout=5)
        content = resp.text.lower()

        checks = [
            ('HTML结构', '<html' in content),
            ('JavaScript', '<script' in content),
            ('报工功能', '报工' in content or '工单' in content),
            ('考勤功能', '考勤' in content or '签到' in content),
        ]

        page_results = []
        for name, check in checks:
            page_results.append({'check': name, 'result': 'OK' if check else 'MISSING'})
            print(f"  {'✅' if check else '❌'} {name}: {'OK' if check else 'MISSING'}")

        test_result = {'name': '页面内容', 'checks': page_results, 'status': 'PASS' if all(c[1] for c in checks) else 'PARTIAL'}
        results['tests'].append(test_result)
    except Exception as e:
        test_result = {'name': '页面内容', 'status': 'FAIL', 'error': str(e)}
        results['tests'].append(test_result)
        print(f"  ❌ FAIL: {e}")

    # 保存报告
    report_file = LOG_DIR / "server_test_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("手机报工服务器测试报告\n")
        f.write("="*60 + "\n\n")
        f.write(f"测试时间: {results['timestamp']}\n")
        f.write(f"服务器: http://localhost:5008\n\n")
        f.write("测试结果:\n")
        for test in results['tests']:
            f.write(f"\n【{test['name']}】")
            if 'status' in test:
                f.write(f" - {test['status']}")
            if 'code' in test:
                f.write(f" (状态码: {test['code']})")
            if 'error' in test:
                f.write(f"\n  错误: {test['error']}")
            if 'checks' in test:
                for check in test['checks']:
                    f.write(f"\n  - {check['check']}: {check['result']}")
        f.write("\n\n" + "="*60 + "\n")
        f.write(f"总计: {results['summary']['passed']} 通过, {results['summary']['failed']} 失败\n")
        f.write("="*60 + "\n")

    print("\n" + "="*60)
    print(f"测试完成: {results['summary']['passed']} 通过, {results['summary']['failed']} 失败")
    print(f"详细报告: {report_file}")
    print("="*60)

    return results

if __name__ == '__main__':
    test_server()
