"""测试报工 API - 验证三个 bug 修复"""
import urllib.request
import json
import sys

BASE = 'http://localhost:5008'

def eprint(*args, **kwargs):
    print(*args, **kwargs, flush=True, file=sys.stdout)

def post(path, data):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(f'{BASE}{path}', data=body,
                                 headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode('utf-8'))

def get(path):
    resp = urllib.request.urlopen(f'{BASE}{path}')
    return json.loads(resp.read().decode('utf-8'))

# 1. 报工前信息
eprint('=== 报工前信息 ===')
info = get('/api/scan-info?code=ORD-202604210003')
data = info.get('data', {})
eprint(f'总进度 completed: {data.get("total_completed_qty")}')
for p in data.get('processes', []):
    if p['completed_qty'] > 0 or p['step_name'] == '包装入库':
        eprint(f'  工序: {p["step_name"]} -> completed_qty: {p["completed_qty"]}')

# 2. 提交报工 - 包装入库，数量 30
eprint('\n=== 提交报工 ===')
ret = post('/api/process_sub_step', {
    'process_id': 'a64471d6-df3e-443a-aa9d-d8c3c303c1f0',
    'order_no': 'ORD-202604210003',
    'step_name': '包装入库',
    'quantity': 30,
    'operator': '王工',
    'remark': '修复验证报工-20260518'
})
eprint(f'code: {ret.get("code")}, message: {ret.get("message")}')
record = ret.get('data', {}).get('record', {})
eprint(f'记录: step_name={record.get("step_name")}, qty={record.get("quantity")}, operator={record.get("operator")}')

# 3. 验证工序进度和总进度
eprint('\n=== 报工后信息 ===')
info2 = get('/api/scan-info?code=ORD-202604210003')
data2 = info2.get('data', {})
eprint(f'总进度 completed: {data2.get("total_completed_qty")}')
for p in data2.get('processes', []):
    if p['completed_qty'] > 0 or p['step_name'] == '包装入库':
        eprint(f'  工序: {p["step_name"]} -> completed_qty: {p["completed_qty"]}')

# 4. 验证报工记录 (从 chengsheng.db)
eprint('\n=== 报工记录 (chengsheng.db) ===')
records = get('/api/sub_step_records?order_no=ORD-202604210003')
if isinstance(records, list):
    eprint(f'记录数: {len(records)}')
    for r in records:
        eprint(f'  {r.get("processName")}: qty={r.get("completedQty")}, worker={r.get("worker")}, time={r.get("time","")[:19]}')
else:
    eprint(f'返回: {json.dumps(records, ensure_ascii=False)}')
