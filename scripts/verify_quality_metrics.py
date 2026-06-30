# -*- coding: utf-8 -*-
"""质量端点埋点端到端验证"""
import sys
import json
import time
import urllib.request
import urllib.error

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE = 'http://127.0.0.1:5008'


def get(path, timeout=5):
    url = f'{BASE}{path}'
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        body = r.read().decode('utf-8', errors='replace')
        return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return e.code, body
    except Exception as e:
        return None, f'{type(e).__name__}: {e}'


def post(path, payload=None, timeout=5):
    url = f'{BASE}{path}'
    data = json.dumps(payload or {}).encode('utf-8')
    req = urllib.request.Request(
        url, data=data, method='POST',
        headers={'Content-Type': 'application/json'}
    )
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        body = r.read().decode('utf-8', errors='replace')
        return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return e.code, body
    except Exception as e:
        return None, f'{type(e).__name__}: {e}'


def reset_stats():
    code, body = post('/api/metrics/reset')
    print(f'  reset: code={code} body={body[:80]}')


def fetch_stats():
    code, body = get('/api/metrics/stats?minutes=5')
    return code, json.loads(body) if code == 200 else body


def fetch_counters():
    code, body = get('/api/metrics/stats?minutes=5')
    if code != 200:
        return {}
    data = json.loads(body)
    return {
        'total_requests': data.get('data', {}).get('api', {}).get('total_requests', 0),
        'top_endpoints': data.get('data', {}).get('api', {}).get('top_endpoints', {}),
        'status_codes': data.get('data', {}).get('api', {}).get('status_codes', {}),
        'reports_total': data.get('data', {}).get('reports', {}).get('total', 0),
        'reports_success': data.get('data', {}).get('reports', {}).get('success', 0),
        'reports_failed': data.get('data', {}).get('reports', {}).get('failed', 0),
        'errors_total': data.get('data', {}).get('errors', {}).get('total', 0),
        'errors_by_type': data.get('data', {}).get('errors', {}).get('by_type', {}),
        'counters': data.get('data', {}).get('counters', {}),
    }


def main():
    print('===== 质量端点埋点端到端验证 =====\n')
    print('[1/6] 重置 stats')
    reset_stats()
    time.sleep(1)

    print('\n[2/6] 调用前 stats 快照')
    before = fetch_counters()
    print(f'  before: {before}')

    print('\n[3/6] GET /api/quality/types')
    code, body = get('/api/quality/types')
    print(f'  code={code} body={body[:120]}')
    time.sleep(0.5)

    print('\n[4/6] GET /api/quality/list?page=1&page_size=5')
    code, body = get('/api/quality/list?page=1&page_size=5')
    print(f'  code={code} body={body[:120]}')
    time.sleep(0.5)

    print('\n[5/6] POST /api/quality/999001/create (质检提交-成功路径)')
    payload = {
        'result': '合格',
        'inspector': 'OP_TEST',
        'order_no': 'PO_TEST_999001',
        'process_id': 'PROC_TEST',
        'inspection_type': '终检',
        'process_name': '测试工序'
    }
    code, body = post('/api/quality/999001/create', payload)
    print(f'  code={code} body={body[:200]}')
    time.sleep(0.5)

    print('\n[5.5/6] POST /api/quality/999002/create (质检提交-触发去重,走失败路径)')
    dup_payload = dict(payload)
    dup_payload['order_no'] = 'PO_TEST_999001'  # 同一 order_no + process_name 重复
    dup_payload['inspector'] = 'OP_DUP'
    code, body = post('/api/quality/999002/create', dup_payload)
    print(f'  code={code} body={body[:200]}')
    time.sleep(0.5)

    print('\n[5.6/6] POST /api/quality/999003/create (质检提交-异常路径,缺字段触发异常)')
    bad_payload = {'inspector': 'OP_BAD'}  # 无 order_no/process_id 可能走完或异常
    code, body = post('/api/quality/999003/create', bad_payload)
    print(f'  code={code} body={body[:200]}')
    time.sleep(0.5)

    print('\n[6/6] 调用后 stats 快照')
    after = fetch_counters()
    print(f'  after:  {after}')

    print('\n===== 增长对比 =====')
    diff_total = after['total_requests'] - before['total_requests']
    diff_reports = after['reports_total'] - before['reports_total']
    diff_errors = after['errors_total'] - before['errors_total']
    print(f'  total_requests:  {before["total_requests"]} -> {after["total_requests"]} (Δ={diff_total})')
    print(f'  reports_total:   {before["reports_total"]} -> {after["reports_total"]} (Δ={diff_reports})')
    print(f'  reports_success: {before["reports_success"]} -> {after["reports_success"]}')
    print(f'  reports_failed:  {before["reports_failed"]} -> {after["reports_failed"]}')
    print(f'  errors_total:    {before["errors_total"]} -> {after["errors_total"]} (Δ={diff_errors})')
    print(f'  top_endpoints:   {after["top_endpoints"]}')
    print(f'  status_codes:    {after["status_codes"]}')
    print(f'  errors_by_type:  {after["errors_by_type"]}')

    print('\n===== 验收 =====')
    checks = [
        ('total_requests 增长 >= 3', diff_total >= 3),
        ('reports_total 增长 >= 1', diff_reports >= 1),
        ('reports_success 增长 >= 1', after['reports_success'] - before['reports_success'] >= 1),
        ('top_endpoints 含 /api/quality/*', any('/api/quality/' in k for k in after['top_endpoints'].keys())),
        ('status_codes 含 200', '200' in after['status_codes'] or 200 in after['status_codes']),
        ('reports_success == reports_total(全部成功)', after['reports_success'] == after['reports_total'] and after['reports_total'] == 3),
    ]
    all_pass = True
    for name, ok in checks:
        mark = '✅' if ok else '❌'
        print(f'  {mark} {name}')
        if not ok:
            all_pass = False

    print('\n' + ('✅ 全部通过' if all_pass else '❌ 有未通过项'))


if __name__ == '__main__':
    main()
