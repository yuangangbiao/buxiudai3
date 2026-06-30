"""综合验证：所有 5008 报工端点"""
import requests
r = requests.post('http://127.0.0.1:5008/api/login', json={'username':'测试','password':'123456'}, timeout=5)
tok = r.json().get('data', {}).get('token', '')
hdr = {'Authorization': f'Bearer {tok}'}

print('=' * 60)
print('【综合验证】5008 报工系统所有任务类型 + 扫码')
print('=' * 60)

endpoints = [
    ('排产任务', '/api/production-orders', None),
    ('工序任务', '/api/all-process-tasks', None),
    ('质检任务', '/api/quality-inspection/tasks', None),
    ('物料任务', '/api/tasks?page_route=material', None),
    ('外协任务', '/api/tasks?page_route=outsource', None),
]
for name, url, body in endpoints:
    r = requests.get(f'http://127.0.0.1:5008{url}', headers=hdr, timeout=10)
    d = r.json()
    if isinstance(d, dict) and d.get('code') == 0:
        data = d.get('data')
        if isinstance(data, list): n = len(data)
        elif isinstance(data, dict):
            if 'tasks' in data: n = len(data['tasks'])
            elif 'data' in data: n = len(data['data'])
            else: n = '?'
        else: n = '?'
        print(f'  {name:12s} {url:50s} -> {r.status_code} {n} 条')
    else:
        msg = d.get('message', '?') if isinstance(d, dict) else '?'
        print(f'  {name:12s} {url:50s} -> {r.status_code} {msg[:60]}')

print()
print('=== 扫码测试 ===')
codes = ['ORD-20260619-0001','ORD-20260416-0001','ORD-202604200001','GO-AUTO-001','WO_TEST001']
for code in codes:
    r = requests.get(f'http://127.0.0.1:5008/api/scan-info?code={code}', headers=hdr, timeout=5)
    d = r.json()
    if isinstance(d, dict) and d.get('code') == 0:
        order_no = d.get('data', {}).get('order_no', '?')
        n_proc = len(d.get('data', {}).get('processes', []))
        print(f'  {code:25s} -> 200 order_no={order_no} 工序数={n_proc}')
    else:
        print(f'  {code:25s} -> {r.status_code} {d.get("message","?")[:50]}')

print()
print('=== 服务健康 ===')
for url in ['http://127.0.0.1:5002/health','http://127.0.0.1:5008/api/health','http://127.0.0.1:8008/health','http://127.0.0.1:5003/health']:
    try:
        r = requests.get(url, timeout=5)
        d = r.json() if r.headers.get('content-type','').startswith('application/json') else {}
        print(f'  {url:50s} -> {r.status_code} status={d.get("status","?") if isinstance(d,dict) else "?"}')
    except Exception as e:
        print(f'  {url:50s} -> ERR {str(e)[:60]}')
