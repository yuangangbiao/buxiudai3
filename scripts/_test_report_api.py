# -*- coding: utf-8 -*-
"""
直接调用 metrics 内部的 report_submitted, 验证 API 工作
(避开 storage 既有 bug, 但埋点调用本身验证)
"""
import sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
import json
import urllib.request

BASE = 'http://127.0.0.1:5008'

# 1. 重置
urllib.request.urlopen(urllib.request.Request(BASE + '/api/metrics/reset', method='POST'), timeout=5)
print('[reset] OK')

# 2. 验证: 通过修改 scan.py 的代码路径, 在 create_sample_task 成功时记录 report_submitted
#    (临时测试,验证 report_submitted 链路通)
#    实际不改业务代码, 而是用一个独立的小程序模拟

# 3. 直接在进程内模拟扫码分配全流程 → 调 metrics 模块
from metrics import metrics

# 模拟扫码分配成功
metrics.api_request('/api/scan/task', 0.05, 200)
metrics.report_submitted(order_id=1, worker_id='OP001', success=True)
metrics.report_submitted(order_id=2, worker_id='OP002', success=True)
metrics.report_submitted(order_id=3, worker_id='OP003', success=False)

# 4. 查 stats
print()
print('--- stats (模拟调用后) ---')
r = urllib.request.urlopen(BASE + '/api/metrics/stats', timeout=5)
data = json.loads(r.read())['data']
print(f"  reports.total       = {data['reports']['total']}")
print(f"  reports.success     = {data['reports']['success']}")
print(f"  reports.failed      = {data['reports']['failed']}")
print(f"  reports.success_rate= {data['reports']['success_rate']}")
print(f"  api.total_requests  = {data['api']['total_requests']}")
print(f"  api.top_endpoints   = {data['api']['top_endpoints']}")
print(f"  api.status_codes    = {data['api']['status_codes']}")
print(f"  errors.total        = {data['errors']['total']}")
print(f"  counters:")
for k, v in data['counters'].items():
    print(f"      {k} = {v}")
