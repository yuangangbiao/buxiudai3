# -*- coding: utf-8 -*-
"""最终验证 - 4 文件埋点整合测试"""
import os, sys, time, json, subprocess, urllib.request, urllib.error
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass

PY = r'C:\Users\lenovo\AppData\Local\Python\bin\python3.14-64.exe'
CWD = r'd:\yuan\不锈钢网带跟单3.0'
SCRIPT = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\app.py'
LOG = r'd:\yuan\不锈钢网带跟单3.0\logs\5008.log'

def http_get(p, timeout=10):
    try:
        r = urllib.request.urlopen(f'http://127.0.0.1:5008{p}', timeout=timeout)
        return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace') if e.fp else ''
    except Exception as e:
        return 0, f'{type(e).__name__}: {e}'

def http_post(p, data, timeout=10):
    payload = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(f'http://127.0.0.1:5008{p}', data=payload,
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read().decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace') if e.fp else ''
    except Exception as e:
        return 0, f'{type(e).__name__}: {e}'

# 1. 重启 5008
print('[1/4] 重启 5008（集成 4 文件埋点）...')
subprocess.run(['powershell', '-NoProfile', '-Command',
    "Get-NetTCPConnection -LocalPort 5008 -ErrorAction SilentlyContinue | "
    "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
], capture_output=True, timeout=10)
time.sleep(2)
log_fp = open(LOG, 'ab', buffering=0)
proc = subprocess.Popen([PY, SCRIPT], cwd=CWD, stdout=log_fp, stderr=log_fp,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
print(f'  PID={proc.pid}')
for i in range(40):
    time.sleep(1)
    try:
        urllib.request.urlopen('http://127.0.0.1:5008/api/health', timeout=3)
        print(f'  READY at {i+1}s')
        break
    except: pass
time.sleep(2)

# 2. 触发业务
print()
print('[2/4] 触发 4 文件业务端点')
print('  - process.my-tasks: GET /api/process/my-tasks?worker_id=15')
s, b = http_get('/api/process/my-tasks?worker_id=15')
print(f'    status={s}  {b[:100]}')

print('  - quality.list: GET /api/quality/list')
s, b = http_get('/api/quality/list')
print(f'    status={s}  {b[:100]}')

print('  - quality.types: GET /api/quality/types')
s, b = http_get('/api/quality/types')
print(f'    status={s}  {b[:100]}')

print('  - scan.workorder: GET /api/scan/workorder/ORD-TEST-001')
s, b = http_get('/api/scan/workorder/ORD-TEST-001')
print(f'    status={s}  {b[:100]}')

print('  - scan.task: POST /api/scan/task')
s, b = http_post('/api/scan/task', {'qr_data': 'WO:ORD-TEST-001'})
print(f'    status={s}  {b[:100]}')

print('  - scan.worker: GET /api/scan/worker/15')
s, b = http_get('/api/scan/worker/15')
print(f'    status={s}  {b[:100]}')

print('  - attendance: GET /api/attendance')
s, b = http_get('/api/attendance')
print(f'    status={s}  {b[:100]}')

print('  - attendance: GET /api/attendance/测试')
import urllib.parse
s, b = http_get(f'/api/attendance/{urllib.parse.quote("测试")}')
print(f'    status={s}  {b[:100]}')

print('  - attendance: POST /api/attendance check-in')
s, b = http_post('/api/attendance', {'action': 'check-in', 'username': '测试'})
print(f'    status={s}  {b[:100]}')

print('  - attendance: POST /api/attendance check-out')
s, b = http_post('/api/attendance', {'action': 'check-out', 'username': '测试'})
print(f'    status={s}  {b[:100]}')

# 3. metrics 统计
print()
print('[3/4] 查 metrics 统计')
time.sleep(2)
s, b = http_get('/api/metrics/stats')
print(f'  /api/metrics/stats  status={s}')
if s == 200:
    data = json.loads(b).get('data', {})
    print(f'  api.total_requests: {data.get("api",{}).get("total_requests")}')
    print(f'  api.status_codes: {data.get("api",{}).get("status_codes")}')
    print(f'  api.top_endpoints: {data.get("api",{}).get("top_endpoints")}')
    print(f'  api.avg_duration_ms: {data.get("api",{}).get("avg_duration_ms")}')
    print(f'  reports.total: {data.get("reports",{}).get("total")}')
    print(f'  reports.success: {data.get("reports",{}).get("success")}')
    print(f'  reports.failed: {data.get("reports",{}).get("failed")}')
    print(f'  errors.total: {data.get("errors",{}).get("total")}')

# 4. health
print()
print('[4/4] 查 metrics health')
s, b = http_get('/api/metrics/health')
print(f'  /api/metrics/health  status={s}')
print(f'  body: {b}')

# 5. 写报告
out = {
    'time': time.strftime('%Y-%m-%d %H:%M:%S'),
    'pid': proc.pid,
    'business_calls': 10,
}
with open(r'd:\yuan\不锈钢网带跟单3.0\docs\metrics_integration_test.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f'\n报告: docs/metrics_integration_test.json')
