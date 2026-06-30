# -*- coding: utf-8 -*-
"""
调用 4 个 scan 端点 + 验证 metrics 增长
"""
import json
import sys
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:5008'

calls = [
    ('GET',  '/api/scan/workorder/WO202604001',  None,                                  'workorder-未找到(预期 2001)'),
    ('POST', '/api/scan/task',                   '{"qr_data":"WO:WO202604001","operator_id":"OP001"}',  'task-扫码分配(可能找不到任务)'),
    ('GET',  '/api/scan/worker/nonexistent_999', None,                                  'worker-不存在(预期 404 + worker_scan_miss)'),
    ('POST', '/api/scan/test/create-sample',     '{"operator_id":"OP001","order_no":"WO_TEST001","process_name":"编织","quantity":50}', 'create-sample(测试端点)'),
]

print('=== 调 4 个 scan 端点 ===')
for method, path, body, label in calls:
    url = BASE + path
    try:
        data = body.encode('utf-8') if body else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={'Content-Type': 'application/json'} if body else {})
        with urllib.request.urlopen(req, timeout=8) as r:
            txt = r.read().decode('utf-8', errors='replace')[:200]
            print(f'[+] {label:48s} status={r.status} body={txt}')
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode('utf-8', errors='replace')[:200] if e.fp else ''
        print(f'[-] {label:48s} status={e.code} body={body_txt}')
    except Exception as e:
        print(f'[!] {label:48s} EXC {type(e).__name__}: {e}')

print()
print('=== /api/metrics/stats (扫后) ===')
with urllib.request.urlopen(BASE + '/api/metrics/stats', timeout=5) as r:
    stats = json.loads(r.read().decode('utf-8'))
data = stats['data']
print(f"  api.total_requests       = {data['api']['total_requests']}")
print(f"  api.error_rate           = {data['api']['error_rate']}")
print(f"  api.top_endpoints        = {data['api']['top_endpoints']}")
print(f"  api.status_codes         = {data['api']['status_codes']}")
print(f"  reports.total            = {data['reports']['total']}")
print(f"  reports.success          = {data['reports']['success']}")
print(f"  reports.success_rate     = {data['reports']['success_rate']}")
print(f"  errors.total             = {data['errors']['total']}")
print(f"  errors.recent (last 5)   =")
for e in data['errors']['recent'][-5:]:
    msg = e['message'][:60]
    print(f"      [{e['error_type']}] {e['endpoint']} - {msg}")
print(f"  counters (全量)          =")
for k, v in data['counters'].items():
    print(f"      {k} = {v}")
