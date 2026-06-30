"""用 SIMULATE_DB_ERROR=1 启动 5008, 验证 record_error 路径"""
import os, sys, time, subprocess, urllib.request, urllib.error
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass

PY = r'C:\Users\lenovo\AppData\Local\Python\bin\python3.14-64.exe'
CWD = r'd:\yuan\不锈钢网带跟单3.0'
SCRIPT = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\app.py'
LOG = r'd:\yuan\不锈钢网带跟单3.0\logs\5008_500path.log'

print('[1/3] 杀掉旧 5008...')
subprocess.run(['powershell', '-NoProfile', '-Command',
    "Get-NetTCPConnection -LocalPort 5008 -ErrorAction SilentlyContinue | "
    "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
], capture_output=True, timeout=10)
time.sleep(2)

print('[2/3] 启动 5008 (SIMULATE_DB_ERROR=1)...')
log_fp = open(LOG, 'ab', buffering=0)
env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'SIMULATE_DB_ERROR': '1'}
proc = subprocess.Popen(
    [PY, SCRIPT],
    cwd=CWD, stdout=log_fp, stderr=log_fp,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    env=env,
)
print('  PID=%d' % proc.pid)

print('[3/3] 等待 metrics_api 蓝图就绪...')
ready = False
for i in range(40):
    time.sleep(1)
    try:
        r = urllib.request.urlopen('http://127.0.0.1:5008/api/health', timeout=3)
        if r.status == 200:
            print('  5008 READY at %ds, status=%d' % (i+1, r.status))
            ready = True
            break
    except Exception:
        if i % 5 == 4:
            print('  waiting %ds...' % (i+1))

if not ready:
    print('  ❌ 5008 未就绪')
    sys.exit(1)

# 触发 500 路径
print()
print('=== 触发 500 路径: GET /api/process/my-tasks?worker_id=test_500 ===')
try:
    r = urllib.request.urlopen('http://127.0.0.1:5008/api/process/my-tasks?worker_id=test_500', timeout=8)
    print('  500 路径 status=%d body=%s' % (r.status, r.read().decode('utf-8', errors='replace')[:300]))
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='replace')[:300] if e.fp else ''
    print('  500 路径 status=%d body=%s' % (e.code, body))

# 验证 record_error
print()
print('=== 验证 /api/metrics/stats 看到 process_error ===')
time.sleep(1)
r = urllib.request.urlopen('http://127.0.0.1:5008/api/metrics/stats?minutes=5', timeout=5)
body = r.read().decode('utf-8', errors='replace')
data = json.loads(body)['data']
print('  api.total_requests =', data['api']['total_requests'])
print('  api.status_codes   =', data['api']['status_codes'])
print('  errors.total       =', data['errors']['total'])
print('  errors.by_type     =', data['errors']['by_type'])
print('  recent errors      =')
for e in data['errors'].get('recent', []):
    print('    -', e.get('error_type'), '|', e.get('message')[:80], '| endpoint=', e.get('endpoint'))
print('DONE')
