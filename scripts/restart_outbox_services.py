# -*- coding: utf-8 -*-
"""重启 dispatch_center (5003) + mobile_api_ai (5008) 以应用 outbox 改动"""
import os, sys, subprocess, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=True)

PYTHON = r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe'
ROOT = Path(__file__).resolve().parent.parent
MAI = ROOT / 'mobile_api_ai'

def kill_port(port: int):
    r = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True)
    killed = []
    for line in r.stdout.splitlines():
        if f':{port}' in line and 'LISTENING' in line:
            parts = line.strip().split()
            if parts and parts[-1].isdigit():
                pid = int(parts[-1])
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
                killed.append(pid)
    return killed

ports = {5003: 'dispatch_center', 5008: 'mobile_api_ai'}
for port, name in ports.items():
    pids = kill_port(port)
    print(f'Killed {name} (port {port}): {pids}')

print('等待端口释放...')
time.sleep(3)

print('启动 dispatch_center (5003)...')
subprocess.Popen(
    [PYTHON, 'standalone_dispatch_server.py'],
    cwd=str(MAI),
    creationflags=subprocess.CREATE_NEW_CONSOLE,
)
print('dispatch_center 已启动')

print('启动 mobile_api_ai (5008)...')
subprocess.Popen(
    [PYTHON, 'app.py'],
    cwd=str(MAI),
    creationflags=subprocess.CREATE_NEW_CONSOLE,
)
print('mobile_api_ai 已启动')

print('全部启动完成')
