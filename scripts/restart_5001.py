# -*- coding: utf-8 -*-
"""重启 5001 服务（确保使用最新代码）"""
import os
import sys
import time
import subprocess
import signal

PY = r'C:\Users\lenovo\AppData\Local\Python\bin\python3.14-64.exe'
CWD = r'd:\yuan\不锈钢网带跟单3.0'
SCRIPT = r'd:\yuan\不锈钢网带跟单3.0\desktop_web\server.py'
LOG = r'd:\yuan\不锈钢网带跟单3.0\logs\5001.log'
os.makedirs(os.path.dirname(LOG), exist_ok=True)

# 1) 杀掉所有 5001 监听进程
print('[1/3] 杀掉旧 5001 进程...')
subprocess.run(['powershell', '-NoProfile', '-Command',
                "Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue | "
                "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; "
                "Get-Process python* -ErrorAction SilentlyContinue | "
                "Where-Object { $_.CommandLine -like '*desktop_web*server*' } | "
                "Stop-Process -Force -ErrorAction SilentlyContinue"
                ], capture_output=True)
time.sleep(2)

# 2) 启动新进程
print('[2/3] 启动新 5001...')
log_fp = open(LOG, 'ab', buffering=0)
proc = subprocess.Popen(
    [PY, SCRIPT],
    cwd=CWD,
    stdout=log_fp,
    stderr=log_fp,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
)
print(f'  PID={proc.pid}')

# 3) 等待就绪
print('[3/3] 等待服务就绪...')
import urllib.request
for i in range(30):
    time.sleep(1)
    try:
        r = urllib.request.urlopen('http://localhost:5001/api/orders', timeout=2)
        print(f'  READY at {i+1}s, status={r.status}')
        break
    except Exception as e:
        if i % 5 == 4:
            print(f'  waiting {i+1}s... last error: {type(e).__name__}')

# 4) 健康检查
print('--- 健康检查 ---')
import urllib.request
for path in ['/api/orders', '/api/quality/list', '/api/process/list', '/api/shipment/company/list']:
    try:
        r = urllib.request.urlopen(f'http://localhost:5001{path}', timeout=5)
        body = r.read()[:200].decode('utf-8', errors='replace')
        print(f'  {path} -> {r.status}  {body[:120]}')
    except Exception as e:
        print(f'  {path} -> ERROR {e}')

print('DONE')
