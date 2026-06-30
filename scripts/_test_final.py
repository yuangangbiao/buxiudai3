# -*- coding: utf-8 -*-
"""
最终验证: 4 个端点 + report_submitted 链路
"""
import json
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:5008'

# 1. reset
urllib.request.urlopen(urllib.request.Request(BASE + '/api/metrics/reset', method='POST'), timeout=5)
print('[reset] OK')

# 2. 4 个端点
endpoints = [
    ('GET',  '/api/scan/workorder/WO202604001',     None,                                                  'workorder-未找到(2001)'),
    ('POST', '/api/scan/task',                      json.dumps({'qr_data': 'WO:WO202604001', 'operator_id': 'OP001'}), 'task-扫码分配(2001)'),
    ('GET',  '/api/scan/worker/nonexistent_888',    None,                                                  'worker-不存在(404)'),
    ('POST', '/api/scan/test/create-sample',        json.dumps({'operator_id': 'OP001', 'order_no': 'WO202604002', 'process_name': '编织', 'quantity': 30}), 'create-sample(200)'),
    ('POST', '/api/scan/test/metric-report',        json.dumps({'order_id': 123, 'worker_id': 'OP001', 'success': True}),  'test/metric-report(200)'),
    ('POST', '/api/scan/test/metric-report',        json.dumps({'order_id': 124, 'worker_id': 'OP002', 'success': True}),  'test/metric-report-2(200)'),
    ('POST', '/api/scan/test/metric-report',        json.dumps({'order_id': 125, 'worker_id': 'OP003', 'success': False}), 'test/metric-report-3-fail(200)'),
]

print()
print('=== 调 4 端点 + 3 次 metric-report(验证 report_submitted) ===')
for method, path, body, label in endpoints:
    url = BASE + path
    try:
        data = body.encode('utf-8') if body else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={'Content-Type': 'application/json'} if body else {})
        with urllib.request.urlopen(req, timeout=8) as r:
            txt = r.read().decode('utf-8', errors='replace')[:140]
            print(f'  [+] {label:35s} status={r.status} {txt}')
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode('utf-8', errors='replace')[:140] if e.fp else ''
        print(f'  [-] {label:35s} status={e.code} {body_txt}')
    except Exception as e:
        print(f'  [!] {label:35s} EXC: {e}')

# 3. 完整 stats
print()
print('=== /api/metrics/stats ===')
with urllib.request.urlopen(BASE + '/api/metrics/stats', timeout=5) as r:
    data = json.loads(r.read())['data']
print(f"  api.total_requests       = {data['api']['total_requests']}")
print(f"  api.error_rate           = {data['api']['error_rate']}")
print(f"  api.top_endpoints        = {data['api']['top_endpoints']}")
print(f"  api.status_codes         = {data['api']['status_codes']}")
print(f"  reports.total            = {data['reports']['total']}")
print(f"  reports.success          = {data['reports']['success']}")
print(f"  reports.failed           = {data['reports']['failed']}")
print(f"  reports.success_rate     = {data['reports']['success_rate']}")
print(f"  errors.total             = {data['errors']['total']}")
print(f"  errors.recent:")
for e in data['errors']['recent'][-10:]:
    print(f"      [{e['error_type']}] {e['endpoint']} - {e['message'][:80]}")
print(f"  counters:")
for k, v in data['counters'].items():
    print(f"      {k} = {v}")
