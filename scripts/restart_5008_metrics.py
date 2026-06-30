# -*- coding: utf-8 -*-
"""重启 5008 + 验证 metrics_api 蓝图注册"""
import os, sys, time, subprocess, urllib.request, urllib.error
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass

PY = r'C:\Users\lenovo\AppData\Local\Python\bin\python3.14-64.exe'
CWD = r'd:\yuan\不锈钢网带跟单3.0'
SCRIPT = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\app.py'
LOG = r'd:\yuan\不锈钢网带跟单3.0\logs\5008.log'

# 1. 杀旧进程
print('[1/3] 杀掉旧 5008...')
subprocess.run(['powershell', '-NoProfile', '-Command',
    "Get-NetTCPConnection -LocalPort 5008 -ErrorAction SilentlyContinue | "
    "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
], capture_output=True, timeout=10)
time.sleep(2)

# 2. 启动
print('[2/3] 启动新 5008...')
log_fp = open(LOG, 'ab', buffering=0)
proc = subprocess.Popen(
    [PY, SCRIPT],
    cwd=CWD, stdout=log_fp, stderr=log_fp,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
)
print(f'  PID={proc.pid}')

# 3. 等就绪
print('[3/3] 等待 metrics_api 蓝图就绪...')
for i in range(40):
    time.sleep(1)
    try:
        r = urllib.request.urlopen('http://127.0.0.1:5008/api/health', timeout=3)
        print(f'  5008 READY at {i+1}s, status={r.status}')
        # 测试 metrics 端点
        time.sleep(2)
        for path in ['/api/metrics/health', '/api/metrics/stats']:
            try:
                r2 = urllib.request.urlopen(f'http://127.0.0.1:5008{path}', timeout=3)
                body = r2.read().decode('utf-8', errors='replace')[:300]
                print(f'  ✅ {path:30s} status={r2.status}  {body}')
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', errors='replace')[:200] if e.fp else ''
                print(f'  ⚠️  {path:30s} status={e.code}  {body[:100]}')
            except Exception as e:
                print(f'  ❌ {path:30s}  {type(e).__name__}: {e}')
        break
    except Exception:
        if i % 5 == 4:
            print(f'  waiting {i+1}s...')
print('DONE')
