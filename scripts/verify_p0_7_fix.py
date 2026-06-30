# -*- coding: utf-8 -*-
"""验证 P0-7 修复 + 重启 5001"""
import os, sys, time, subprocess, urllib.request, urllib.error
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass

PY = r'C:\Users\lenovo\AppData\Local\Python\bin\python3.14-64.exe'
CWD = r'd:\yuan\不锈钢网带跟单3.0'
SCRIPT = r'd:\yuan\不锈钢网带跟单3.0\desktop_web\server.py'
LOG = r'd:\yuan\不锈钢网带跟单3.0\logs\5001.log'

# 1. 语法检查
print('[1/4] 语法检查...')
r = subprocess.run([PY, '-c', f'import ast; ast.parse(open(r"{SCRIPT}").read()); print("SYNTAX_OK")'],
    capture_output=True, text=True, timeout=15)
print(f'  {r.stdout.strip()}  {r.stderr.strip()[:200]}')

# 2. 杀旧
print('[2/4] 杀旧 5001...')
subprocess.run(['powershell', '-NoProfile', '-Command',
    "Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue | "
    "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
], capture_output=True, timeout=10)
time.sleep(2)

# 3. 启动
print('[3/4] 启动新 5001...')
log_fp = open(LOG, 'ab', buffering=0)
proc = subprocess.Popen([PY, SCRIPT], cwd=CWD, stdout=log_fp, stderr=log_fp,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
print(f'  PID={proc.pid}')
for i in range(40):
    time.sleep(1)
    try:
        urllib.request.urlopen('http://127.0.0.1:5001/api/orders', timeout=3)
        print(f'  READY at {i+1}s')
        break
    except: pass

# 4. 测 admin-list
print('[4/4] 测 /api/process/admin-list ...')
time.sleep(1)
try:
    r = urllib.request.urlopen('http://127.0.0.1:5001/api/process/admin-list', timeout=8)
    body = r.read().decode('utf-8', errors='replace')[:300]
    print(f'  ✅ status={r.status}  {body[:200]}')
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8', errors='replace') if e.fp else ''
    if e.code == 500 and 'po.customer_name' in body:
        print(f'  ❌ 仍报 po.customer_name 错误: {body[:200]}')
    elif e.code == 500 and 'o.customer_name' in body:
        print(f'  ❌ orders 表无 customer_name 字段: {body[:200]}')
    elif e.code == 401:
        print(f'  ✅ 401 UNAUTHORIZED（鉴权拦截，需要登录）— SQL 已不报错')
    else:
        print(f'  ⚠️ status={e.code}  {body[:200]}')
except Exception as e:
    print(f'  ❌ {type(e).__name__}: {e}')

print('DONE')
