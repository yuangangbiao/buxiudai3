# -*- coding: utf-8 -*-
"""
更详细诊断: 验证 task 端点的 report_submitted
"""
import json
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:5008'

# 1. 重置
urllib.request.urlopen(urllib.request.Request(BASE + '/api/metrics/reset', method='POST'), timeout=5)
print('[reset] OK')

# 2. 创建任务 (operator=OP001)
print()
print('--- create-sample: order_no=WO202604999, operator=OP001 ---')
body = json.dumps({
    'operator_id': 'OP001',
    'order_no': 'WO202604999',
    'process_name': '编织',
    'quantity': 50
}).encode('utf-8')
r = urllib.request.urlopen(urllib.request.Request(
    BASE + '/api/scan/test/create-sample', data=body, method='POST',
    headers={'Content-Type': 'application/json'}), timeout=8)
data = json.loads(r.read())
print(f'  resp = {json.dumps(data, ensure_ascii=False)}')

# 3. 调 task 端点, 多种 qr_data 变体
for qr in ['WO:WO202604999', 'WO202604999', 'ORD:WO202604999']:
    print()
    print(f'--- task qr_data={qr!r} ---')
    body = json.dumps({'qr_data': qr, 'operator_id': 'OP001'}).encode('utf-8')
    r = urllib.request.urlopen(urllib.request.Request(
        BASE + '/api/scan/task', data=body, method='POST',
        headers={'Content-Type': 'application/json'}), timeout=8)
    data = json.loads(r.read())
    print(f'  resp = {json.dumps(data, ensure_ascii=False)[:300]}')

# 4. 调 workorder 端点 (测试 content.order_no 匹配)
print()
print('--- workorder WO202604999 ---')
r = urllib.request.urlopen(BASE + '/api/scan/workorder/WO202604999', timeout=8)
data = json.loads(r.read())
print(f'  resp = {json.dumps(data, ensure_ascii=False)[:300]}')

# 5. 看 stats
print()
print('--- stats ---')
r = urllib.request.urlopen(BASE + '/api/metrics/stats', timeout=5)
data = json.loads(r.read())['data']
print(f"  reports.total       = {data['reports']['total']}")
print(f"  api.total_requests  = {data['api']['total_requests']}")
print(f"  api.top_endpoints   = {data['api']['top_endpoints']}")
print(f"  api.status_codes    = {data['api']['status_codes']}")
print(f"  errors.recent:")
for e in data['errors']['recent'][-10:]:
    print(f"      [{e['error_type']}] {e['endpoint']} - {e['message'][:60]}")
print(f"  counters:")
for k, v in data['counters'].items():
    print(f"      {k} = {v}")
