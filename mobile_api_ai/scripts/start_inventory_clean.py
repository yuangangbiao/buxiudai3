# -*- coding: utf-8 -*-
"""干净启动 inventory_api_server：在脚本内 load .env（override=True）覆盖 IDE 注入"""
import os
import sys
import subprocess
import time
import socket
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(r'd:\yuan\不锈钢网带跟单3.0')
LOG = ROOT / 'logs' / 'inventory_manual.log'
LOG.parent.mkdir(exist_ok=True)

# 1) 在脚本内显式 load .env，override=True 强制覆盖 IDE 注入的旧值
load_dotenv(ROOT / '.env', override=True)
print('After load_dotenv:')
print('  HASH:', os.environ.get('INVENTORY_ADMIN_PASSWORD_HASH', '(missing)')[:50])
print('  FLASK_SECRET_KEY len:', len(os.environ.get('FLASK_SECRET_KEY', '')))

# 2) 杀 5010
out = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True, shell=True).stdout
for line in out.splitlines():
    if ':5010' in line and 'LISTENING' in line:
        pid = line.strip().split()[-1]
        if pid.isdigit():
            subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, text=True, shell=True)
            print(f'Killed PID {pid}')

time.sleep(2)

# 3) 启动新进程（env 字典包含已 override 的新值）
log_fp = open(LOG, 'a', encoding='utf-8')
proc = subprocess.Popen(
    [sys.executable, str(ROOT / 'mobile_api_ai' / 'inventory_api_server.py')],
    cwd=str(ROOT / 'mobile_api_ai'),
    env=os.environ.copy(),  # 已包含 .env override 后的新值
    stdout=log_fp,
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)
print(f'Started PID {proc.pid}')

# 4) 等待端口
for i in range(20):
    try:
        with socket.create_connection(('127.0.0.1', 5010), timeout=1):
            print(f'Port 5010 ready (i={i}s)')
            break
    except OSError:
        time.sleep(1)
else:
    print('Port 5010 not ready')
    sys.exit(1)

# 5) 把 PID 写入文件供后续使用
Path(ROOT / 'logs' / 'inventory.pid').write_text(str(proc.pid), encoding='utf-8')
print(f'PID file: logs/inventory.pid')
