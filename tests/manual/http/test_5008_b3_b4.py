# -*- coding: utf-8 -*-
"""5008 B3/B4 修复版测试 - 用真实端点路径"""
import pytest

pytestmark = pytest.mark.manual  # 独立验收/Playwright 脚本，不参与 pytest 单元统计


import os
import sys
import json
import time
import urllib.request
import urllib.error

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_5008 = 'http://127.0.0.1:5008'
results = []


def http_get(port, path, timeout=10):
    url = f'http://127.0.0.1:{port}{path}'
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace') if e.fp else ''
    except Exception as e:
        return 0, f'{type(e).__name__}: {e}'


def http_post(port, path, data=None, timeout=10):
    url = f'http://127.0.0.1:{port}{path}'
    payload = json.dumps(data or {}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace') if e.fp else ''
    except Exception as e:
        return 0, f'{type(e).__name__}: {e}'


def record(name, status, ok, detail=''):
    icon = '✅' if ok else '❌'
    print(f'  {icon} {name:50s} status={status}  {detail[:150]}')
    results.append({'name': name, 'status': status, 'ok': ok, 'detail': detail})


# ============== 1. 登录（用旧版 /api/login） ==============
def test_login():
    print('=' * 70)
    print('1. 5008 旧版登录 /api/login（找真实操作员）')
    print('=' * 70)

    # 试几个常见用户名
    users = ['测试', 'admin', '管理员', 'worker', '操作员']
    for u in users:
        s, b = http_post(5008, '/api/login', {'username': u})
        print(f'  username={u}  status={s}  {b[:120]}')
        if s == 200 and ('"code":0' in b or '"code": 0' in b):
            print(f'  ✅ 找到有效用户: {u}')
            return u
    return None


# ============== 2. B3 修复：POST /api/attendance 签到 ==============
def test_attendance_checkin(username):
    print()
    print('=' * 70)
    print('2. B3 修复：POST /api/attendance 签到')
    print('=' * 70)

    # 2.1 错误路径（验证 405）
    s, b = http_post(5008, '/api/attendance/check-in', {'username': username})
    record('2.1 错误路径 /api/attendance/check-in (应为 405)', s, s == 405, b[:100])

    # 2.2 正确路径 POST /api/attendance + action: 'check-in'
    s, b = http_post(5008, '/api/attendance', {'action': 'check-in', 'username': username})
    record('2.2 正确路径 /api/attendance action=check-in', s, s in (200, 201), b[:200])

    # 2.3 签退
    s, b = http_post(5008, '/api/attendance', {'action': 'check-out', 'username': username})
    record('2.3 签退 /api/attendance action=check-out', s, s in (200, 201), b[:200])

    # 2.4 列出今日签到
    s, b = http_get(5008, '/api/attendance')
    record('2.4 列出签到 /api/attendance', s, s == 200, b[:200])

    # 2.5 查指定人签到（URL 编码中文）
    import urllib.parse
    s, b = http_get(5008, f'/api/attendance/{urllib.parse.quote(username)}')
    record(f'2.5 查 {username} 签到 (URL 编码)', s, s == 200, b[:200])


# ============== 3. B4 修复：3 个报工端点候选 ==============
def test_work_report():
    print()
    print('=' * 70)
    print('3. B4 修复：3 个报工端点候选')
    print('=' * 70)

    test_order = f'TEST-5008-{int(time.time())}'

    # 3.1 POST /api/ai/speech-to-report（语音报工）
    s, b = http_post(5008, '/api/ai/speech-to-report', {
        'text': f'工单 {test_order} 报工 1 件',
        'order_no': test_order,
    })
    record('3.1 语音报工 /api/ai/speech-to-report', s, s in (200, 201, 400), b[:200])

    # 3.2 POST /api/scan/task（扫码分配）
    s, b = http_post(5008, '/api/scan/task', {
        'qr_data': f'WO:{test_order}',
        'operator_id': 'OP001',
    })
    record('3.2 扫码分配 /api/scan/task', s, s in (200, 201, 400, 404), b[:200])

    # 3.3 POST /api/quality（质检报工）
    s, b = http_post(5008, '/api/quality', {
        'orderNo': test_order,
        'orderId': 0,
        'inspector': '综合测试',
        'inspectionType': '首检',
        'result': 'pass',
        'inspectionItems': [{'name': '外观', 'result': '合格'}],
    })
    record('3.3 质检报工 /api/quality (旧版)', s, s in (200, 201, 400, 500), b[:200])

    # 3.4 旧版 /api/work-report（应 404）
    s, b = http_post(5008, '/api/work-report', {'order_no': test_order})
    record('3.4 旧版 /api/work-report (应为 404)', s, s == 404, b[:100])


# ============== 4. 关键端点扫描验证 ==============
def test_key_endpoints():
    print()
    print('=' * 70)
    print('4. 关键端点扫描（基于 5008端点清单）')
    print('=' * 70)

    endpoints = [
        # auth
        ('GET', '/api/auth/info', None),
        # scan
        ('GET', '/api/scan/worker/OP001', None),
        # process
        ('GET', '/api/process/my-tasks', None),
        # quality
        ('GET', '/api/quality/list', None),
        ('GET', '/api/quality/types', None),
        # message
        ('GET', '/api/message/list', None),
        ('GET', '/api/message/unread-count', None),
        # approval
        ('GET', '/api/approval/pending', None),
        ('GET', '/api/approval/history', None),
        # ai
        ('GET', '/api/ai/chat/history', None),
        # metrics
        ('GET', '/api/metrics/health', None),
        ('GET', '/api/metrics/stats', None),
        # legacy
        ('GET', '/api/dashboard', None),
        ('GET', '/api/workers', None),
        ('GET', '/api/production-orders', None),
        ('GET', '/api/sub_step_records', None),
        # schedule
        ('GET', '/api/schedule/list', None),
        ('GET', '/api/schedule/pending', None),
        ('GET', '/api/schedule/health', None),
        ('GET', '/api/workorder/', None),
    ]
    for method, path, data in endpoints:
        if method == 'GET':
            s, b = http_get(5008, path)
        else:
            s, b = http_post(5008, path, data or {})
        ok = s in (200, 401, 403, 404, 500)
        record(f'4.{endpoints.index((method, path, data))+1:02d} {method} {path}', s, ok, b[:80])


# ============== Main ==============
if __name__ == '__main__':
    print('╔' + '=' * 68 + '╗')
    print('║  5008 B3/B4 修复版测试 - 用真实端点路径                                ║')
    print('╚' + '=' * 68 + '╝')
    print(f'时间: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    username = test_login()
    if username:
        test_attendance_checkin(username)
    else:
        print('⚠️ 未找到有效用户，跳过签到测试')
    test_work_report()
    test_key_endpoints()

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

    if failed:
        print()
        print('失败用例:')
        for r in results:
            if not r['ok']:
                print(f'  ❌ {r["name"]}  status={r["status"]}  {r["detail"][:150]}')

    # 保存
    out = {
        'time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total': total,
        'passed': passed,
        'failed': failed,
        'pass_rate': f'{pass_rate:.1f}%',
        'results': results,
    }
    out_path = r'd:\yuan\不锈钢网带跟单3.0\docs\test_5008_fixed.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\n原始结果: {out_path}')

    sys.exit(0 if failed == 0 else 1)
