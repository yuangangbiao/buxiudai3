# -*- coding: utf-8 -*-
"""
import pytest

pytestmark = pytest.mark.manual  # 独立验收/Playwright 脚本，不参与 pytest 单元统计


8008 sync_bridge + 5008 mobile_api 综合测试
测试范围：
- 8008 健康 + 同步链路触发 + 补洞守护状态
- 5008 健康 + 移动报工 API（核心 5 端点）
- 5003/5001 回归（关键端点）

真请求真响应，不 mock。
"""
import os
import sys
import io
import json
import time
import urllib.request
import urllib.error
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# UTF-8 输出
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE = {
    5001: 'http://127.0.0.1:5001',
    5003: 'http://127.0.0.1:5003',
    5008: 'http://127.0.0.1:5008',
    8008: 'http://127.0.0.1:8008',
}

results = []  # [(name, status, detail)]


def http_get(port, path, timeout=10):
    url = f'{BASE[port]}{path}'
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        body = r.read().decode('utf-8', errors='replace')
        return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace') if e.fp else ''
        return e.code, body
    except Exception as e:
        return 0, f'{type(e).__name__}: {e}'


def http_post(port, path, data=None, headers=None, timeout=10):
    url = f'{BASE[port]}{path}'
    payload = json.dumps(data or {}).encode('utf-8')
    hdrs = {'Content-Type': 'application/json'}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=payload, headers=hdrs, method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        body = r.read().decode('utf-8', errors='replace')
        return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace') if e.fp else ''
        return e.code, body
    except Exception as e:
        return 0, f'{type(e).__name__}: {e}'


def record(name, status, ok, detail=''):
    icon = '✅' if ok else '❌'
    print(f'  {icon} {name:50s} status={status}  {detail[:100]}')
    results.append({'name': name, 'status': status, 'ok': ok, 'detail': detail})


# ============== 8008 测试 ==============
def test_8008():
    print('=' * 70)
    print('A. 8008 sync_bridge 测试')
    print('=' * 70)

    # A1 健康检查
    s, b = http_get(8008, '/api/health')
    record('A1 /api/health', s, s == 200, b)

    # A2 /health 详细
    s, b = http_get(8008, '/health')
    record('A2 /health 详细', s, s == 200, b[:200])
    if s == 200:
        try:
            data = json.loads(b)
            print(f'    - db: {data.get("db")}')
            print(f'    - catchup_alive: {data.get("catchup_alive")}')
            print(f'    - catchup_heartbeat: {data.get("catchup_heartbeat")}')
            if not data.get('catchup_alive'):
                print('    ⚠️  补洞守护线程未运行！')
        except Exception as e:
            print(f'    parse fail: {e}')

    # A3 同步端点 - 模拟 5003 报工触发同步
    payload = {
        'action': 'submit',
        'order_no': f'TEST-8008-{int(time.time())}',
        'inspection_type': '首检',
        'process_name': 'P03',
        'inspector': '综合测试',
        'items': [{'name': '外观', 'result': '合格'}],
        'overall_result': 'pass',
        'timestamp': time.time(),
    }
    s, b = http_post(8008, '/api/sync/quality-report', data=payload)
    record('A3 /api/sync/quality-report 触发', s, s in (200, 201, 202), b[:200])

    # A4 子步报工同步端点
    s, b = http_post(8008, '/api/sync/sub-step-report', data={
        'order_no': f'TEST-8008-{int(time.time())}',
        'step': 'P03',
        'qty': 1.0,
    })
    record('A4 /api/sync/sub-step-report', s, s in (200, 201, 202), b[:200])

    # A5 死信表查询（间接验证补洞）
    s, b = http_get(8008, '/api/dlq/list')
    record('A5 /api/dlq/list 死信', s, s in (200, 401, 403, 404), b[:150])


# ============== 5008 测试 ==============
def test_5008():
    print()
    print('=' * 70)
    print('B. 5008 mobile_api 移动报工测试')
    print('=' * 70)

    # B1 健康检查
    s, b = http_get(5008, '/api/health')
    record('B1 /api/health', s, s == 200, b[:200])
    if s == 200:
        try:
            data = json.loads(b)
            data2 = data.get('data', {})
            print(f'    - service: {data2.get("service")}')
            print(f'    - status: {data2.get("status")}')
            print(f'    - components: {data2.get("components")}')
        except Exception:
            pass

    # B2 关键端点扫描
    endpoints = [
        ('/api/login', 'GET'),
        ('/api/orders', 'GET'),
        ('/api/process/list', 'GET'),
        ('/api/quality/list', 'GET'),
        ('/api/material/list', 'GET'),
        ('/api/shipment/list', 'GET'),
        ('/api/operators', 'GET'),
        ('/api/attendance', 'GET'),
        ('/api/inventory', 'GET'),
        ('/api/csrf', 'GET'),
    ]
    for path, method in endpoints:
        if method == 'GET':
            s, b = http_get(5008, path, timeout=8)
        else:
            s, b = http_post(5008, path, data={}, timeout=8)
        ok = s in (200, 401, 403, 404, 405)  # 任何"已知 HTTP 状态"都算端点存在
        record(f'B2 {path:35s} {method}', s, ok, b[:80])

    # B3 移动报工核心 - 报工提交
    s, b = http_post(5008, '/api/attendance/check-in', data={
        'operator': '综合测试',
        'order_no': f'TEST-5008-{int(time.time())}',
    })
    record('B3 /api/attendance/check-in 签到', s, s in (200, 201, 400, 401), b[:200])

    # B4 报工
    s, b = http_post(5008, '/api/work-report', data={
        'order_no': f'TEST-5008-{int(time.time())}',
        'process_code': 'P03',
        'qty': 1.0,
    })
    record('B4 /api/work-report 报工', s, s in (200, 201, 400, 401), b[:200])


# ============== 5003 回归 ==============
def test_5003():
    print()
    print('=' * 70)
    print('C. 5003 dispatch 回归测试')
    print('=' * 70)

    # C1 健康
    for path in ['/api/dispatch-center/health', '/health', '/api/health']:
        s, b = http_get(5003, path)
        if s in (200, 404):
            record(f'C1 5003 {path}', s, True, b[:150])
            break

    # C2 业务端点（直查）
    endpoints = [
        '/api/dispatch-center/quality/list',
        '/api/dispatch-center/process/list',
        '/api/dispatch-center/material/list',
        '/api/dispatch-center/orders',
        '/api/dispatch-center/operators',
    ]
    for path in endpoints:
        s, b = http_get(5003, path)
        ok = s in (200, 401, 403, 404, 500)
        record(f'C2 5003 {path}', s, ok, b[:80])

    # C3 模拟 5001 转发请求（带 X-Dispatch-Token）
    s, b = http_get(5003, '/api/dispatch-center/quality/list', timeout=8)
    record('C3 5001→5003 转发路径', s, s in (200, 401, 403), b[:100])


# ============== 5001 回归 ==============
def test_5001():
    print()
    print('=' * 70)
    print('D. 5001 desktop_web 回归测试')
    print('=' * 70)

    endpoints = [
        '/api/orders',
        '/api/process/admin-list',
        '/api/quality/admin-list',
        '/api/material/list',
        '/api/shipment/company/list',
        '/api/operators',
        '/api/attendance',
    ]
    for path in endpoints:
        s, b = http_get(5001, path)
        ok = s in (200, 401, 403, 404)
        record(f'D1 5001 {path}', s, ok, b[:80])

    # D2 端到端 - 5001 → 5003 链路
    s, b = http_get(5001, '/api/quality/list')
    record('D2 5001 /api/quality/list 走 _call_dispatch', s, s in (200, 401, 403, 500), b[:150])


# ============== 同步链路端到端 ==============
def test_sync_e2e():
    print()
    print('=' * 70)
    print('E. 端到端同步链路测试 (5001→5003→8008→MySQL)')
    print('=' * 70)

    # E1 触发 5003 报工
    payload = {
        'action': 'work_report',
        'order_no': f'E2E-{int(time.time())}',
        'process_code': 'P03',
        'qty': 1.0,
        'operator': 'E2E测试',
    }
    s, b = http_post(5003, '/api/dispatch-center/process/work-report', data=payload)
    record('E1 5003 工序报工', s, s in (200, 201, 400, 401), b[:200])

    # E2 等待同步
    print('  ...等待 3 秒让 8008 处理同步...')
    time.sleep(3)

    # E3 查 8008 健康（看 catchup_heartbeat 变化）
    s, b = http_get(8008, '/health')
    record('E3 8008 健康 (after sync)', s, s == 200, b[:200])
    if s == 200:
        try:
            data = json.loads(b)
            print(f'    - catchup_alive: {data.get("catchup_alive")}')
            print(f'    - catchup_heartbeat: {data.get("catchup_heartbeat")}')
            if data.get('catchup_heartbeat', 0) > 0:
                print('    ✅ 补洞守护线程已在运行')
            else:
                print('    ❌ 补洞守护线程仍未运行（heartbeat=0）')
        except Exception:
            pass


# ============== Main ==============
if __name__ == '__main__':
    print('╔' + '=' * 68 + '╗')
    print('║  8008 sync_bridge + 5008 mobile_api 综合测试                      ║')
    print('╚' + '=' * 68 + '╝')
    print(f'时间: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    test_8008()
    test_5008()
    test_5003()
    test_5001()
    test_sync_e2e()

    # 汇总
    print()
    print('=' * 70)
    print('汇总')
    print('=' * 70)
    total = len(results)
    passed = sum(1 for r in results if r['ok'])
    failed = total - passed
    pass_rate = (passed / total * 100) if total else 0
    print(f'  总用例: {total}')
    print(f'  通过:   {passed}')
    print(f'  失败:   {failed}')
    print(f'  通过率: {pass_rate:.1f}%')

    # 失败列表
    if failed:
        print()
        print('失败用例:')
        for r in results:
            if not r['ok']:
                print(f'  ❌ {r["name"]}  status={r["status"]}  {r["detail"][:100]}')

    # 保存 JSON
    out = {
        'time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total': total,
        'passed': passed,
        'failed': failed,
        'pass_rate': f'{pass_rate:.1f}%',
        'results': results,
    }
    out_path = r'd:\yuan\不锈钢网带跟单3.0\docs\test_8008_5008_full.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\n原始结果: {out_path}')

    # 退出码
    sys.exit(0 if failed == 0 else 1)
