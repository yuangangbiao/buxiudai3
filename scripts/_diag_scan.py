# -*- coding: utf-8 -*-
"""
深度诊断: 看 worker 和 create-sample 端点的 metrics 是否真的调用
"""
import json
import urllib.request

BASE = 'http://127.0.0.1:5008'

# 1. 先 reset
urllib.request.urlopen(urllib.request.Request(BASE + '/api/metrics/reset', method='POST'), timeout=5)
print('[reset] OK')

# 2. 调 worker 端点
print()
print('--- 调 /api/scan/worker/nonexistent_999 ---')
try:
    r = urllib.request.urlopen(BASE + '/api/scan/worker/nonexistent_999', timeout=8)
    print(f'  status={r.status}')
    print(f'  body={r.read().decode("utf-8")[:200]}')
except Exception as e:
    print(f'  EXC: {e}')

# 3. 调 create-sample 端点
print()
print('--- 调 /api/scan/test/create-sample ---')
body = json.dumps({'operator_id': 'OP001', 'order_no': 'WO_TEST002', 'process_name': '编织', 'quantity': 10}).encode('utf-8')
try:
    r = urllib.request.urlopen(urllib.request.Request(BASE + '/api/scan/test/create-sample', data=body, method='POST', headers={'Content-Type': 'application/json'}), timeout=8)
    print(f'  status={r.status}')
    print(f'  body={r.read().decode("utf-8")[:200]}')
except Exception as e:
    print(f'  EXC: {e}')

# 4. 立即看 stats
print()
print('--- /api/metrics/stats (诊断) ---')
r = urllib.request.urlopen(BASE + '/api/metrics/stats', timeout=5)
data = json.loads(r.read())['data']
print(f"  api.total_requests = {data['api']['total_requests']}")
print(f"  api.top_endpoints  = {data['api']['top_endpoints']}")
print(f"  api.status_codes   = {data['api']['status_codes']}")
print(f"  errors.total       = {data['errors']['total']}")
print(f"  errors.recent:")
for e in data['errors']['recent'][-10:]:
    print(f"      [{e['error_type']}] {e['endpoint']} - {e['message'][:80]}")
print(f"  counters:")
for k, v in data['counters'].items():
    print(f"      {k} = {v}")
