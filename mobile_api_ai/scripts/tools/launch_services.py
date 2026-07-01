import subprocess
import sys
import os
import time

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROCS = []

services = [
    ('容器中心(5002)', 'container_center_api.py'),
    ('报工API(5000)', 'app.py'),
    ('微信服务(5003)', 'wechat_server.py'),
]

for name, script in services:
    p = subprocess.Popen(
        [sys.executable, os.path.join(BASE, script)],
        cwd=BASE,
        stdout=open(os.path.join(BASE, f'log_{script}.txt'), 'w'),
        stderr=subprocess.STDOUT,
    )
    PROCS.append(p)
    print(f'[{name}] PID={p.pid}')
    time.sleep(2)

print(f'\n3 services started. PIDs: {[p.pid for p in PROCS]}')
print('Check logs: log_container_center_api.py.txt, log_app.py.txt, log_wechat_server.py.txt')
