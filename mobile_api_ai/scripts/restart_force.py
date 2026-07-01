# -*- coding: utf-8 -*-
"""暴力重启：杀 5010 → 强制等 3s → 启动新进程"""
import os
import sys
import subprocess
import time
import socket
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)
ROOT = Path(r'd:\yuan\不锈钢网带跟单3.0')
LOG = ROOT / 'logs' / 'inventory_manual.log'
LOG.parent.mkdir(exist_ok=True)

# 1) 找所有 5010 进程并杀
out = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True, shell=True).stdout
pids_killed = []
for line in out.splitlines():
    if ':5010' in line and 'LISTENING' in line:
        parts = line.strip().split()
        if parts and parts[-1].isdigit():
            pid = int(parts[-1])
            if pid not in pids_killed:
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, text=True, shell=True)
                pids_killed.append(pid)
print(f'Killed: {pids_killed}')

# 2) 等端口释放
for i in range(10):
    try:
        with socket.create_connection(('127.0.0.1', 5010), timeout=0.5):
            time.sleep(0.5)
    except OSError:
        print(f'Port released after {i*0.5}s')
        break
else:
    print('Port still busy after 5s')

# 3) 启动
log_fp = open(LOG, 'a', encoding='utf-8')
proc = subprocess.Popen(
    [sys.executable, '-u', str(ROOT / 'mobile_api_ai' / 'inventory_api_server.py')],
    cwd=str(ROOT / 'mobile_api_ai'),
    env=os.environ.copy(),
    stdout=log_fp,
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)
print(f'Started PID {proc.pid}')

# 4) 等待 + 探测
for i in range(15):
    try:
        with socket.create_connection(('127.0.0.1', 5010), timeout=1):
            import urllib.request
            r = urllib.request.urlopen('http://127.0.0.1:5010/login', timeout=2)
            if r.status == 200:
                print(f'Port 5010 ready + /login 200 (i={i}s)')
                break
    except Exception:
        time.sleep(1)

Path(ROOT / 'logs' / 'inventory.pid').write_text(str(proc.pid), encoding='utf-8')
