# -*- coding: utf-8 -*-
"""
验证 /api/scan/task 成功分配后的 report_submitted 埋点
"""
import json
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:5008'

# 1. 重置 metrics
urllib.request.urlopen(urllib.request.Request(BASE + '/api/metrics/reset', method='POST'), timeout=5)
print('[reset] OK')

# 2. 用 create-sample 创建一个任务
print()
print('--- 调 create-sample 创建任务(OP001) ---')
body = json.dumps({
    'operator_id': 'OP001',
    'order_no': 'WO202604888',
    'process_name': '编织',
    'quantity': 50
}).encode('utf-8')
r = urllib.request.urlopen(urllib.request.Request(
    BASE + '/api/scan/test/create-sample',
    data=body, method='POST',
    headers={'Content-Type': 'application/json'}
), timeout=8)
data = json.loads(r.read())
print(f'  status={r.status} body={json.dumps(data, ensure_ascii=False)}')

# 3. 再调 task 端点扫码分配这个任务
print()
print('--- 调 /api/scan/task 扫码 WO202604888 + OP001 ---')
body = json.dumps({
    'qr_data': 'WO202604888',
    'operator_id': 'OP001'
}).encode('utf-8')
r = urllib.request.urlopen(urllib.request.Request(
    BASE + '/api/scan/task',
    data=body, method='POST',
    headers={'Content-Type': 'application/json'}
), timeout=8)
data = json.loads(r.read())
print(f'  status={r.status} body={json.dumps(data, ensure_ascii=False)[:300]}')

# 4. 查 reports 统计(看 report_submitted 是否生效)
print()
print('--- /api/metrics/stats (task分配后) ---')
r = urllib.request.urlopen(BASE + '/api/metrics/stats', timeout=5)
stats = json.loads(r.read())['data']
print(f"  reports.total       = {stats['reports']['total']}")
print(f"  reports.success     = {stats['reports']['success']}")
print(f"  reports.failed      = {stats['reports']['failed']}")
print(f"  reports.success_rate= {stats['reports']['success_rate']}")
print(f"  api.total_requests  = {stats['api']['total_requests']}")
print(f"  api.top_endpoints   = {stats['api']['top_endpoints']}")
print(f"  api.status_codes    = {stats['api']['status_codes']}")
print(f"  counters (reports):")
for k, v in stats['counters'].items():
    if 'report' in k.lower():
        print(f"      {k} = {v}")
print(f"  all counters:")
for k, v in stats['counters'].items():
    print(f"      {k} = {v}")
