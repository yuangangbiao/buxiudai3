# -*- coding: utf-8 -*-
"""启动 cloud_relay.py (5005) - 设置正确的 PYTHONPATH"""
import subprocess
import sys
import os
import time
import socket

PYTHON = sys.executable
SCRIPT = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\cloud_relay.py'
WORKDIR = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
# core 模块在上层目录
PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
PORT = 5005

def is_port_open(port):
    s = socket.socket()
    r = s.connect_ex(('127.0.0.1', port))
    s.close()
    return r == 0

def kill_port(port):
    r = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if f':{port}' in line and 'LISTENING' in line:
            pid = line.split()[-1]
            subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
            print(f'Killed PID {pid}')
            return True
    return False

if is_port_open(PORT):
    import http.client
    c = http.client.HTTPConnection('127.0.0.1', PORT, timeout=3)
    c.request('POST', '/api/stats/push', b'{}', {'Content-Type': 'application/json'})
    resp = c.getresponse()
    print(f'5005 running. /api/stats/push -> HTTP {resp.status}')
    c.close()
    if resp.status == 404:
        print('Old code version. Restarting...')
        kill_port(PORT)
        time.sleep(2)
    else:
        sys.exit(0)

# Set PYTHONPATH to include project root (for 'core' module)
env = os.environ.copy()
old_path = env.get('PYTHONPATH', '')
env['PYTHONPATH'] = f'{PROJECT_ROOT};{WORKDIR};{old_path}'

print('Starting cloud_relay.py with PYTHONPATH...')
proc = subprocess.Popen(
    [PYTHON, SCRIPT],
    cwd=WORKDIR,
    env=env,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0,
)
print(f'Started PID={proc.pid}')

for i in range(10):
    time.sleep(1)
    if is_port_open(PORT):
        print(f'SUCCESS: cloud_relay.py running on port {PORT}')
        # Test the endpoint
        import http.client
        c = http.client.HTTPConnection('127.0.0.1', PORT, timeout=3)
        c.request('POST', '/api/stats/push', b'{}', {'Content-Type': 'application/json'})
        resp = c.getresponse()
        body = c.read().decode()
        print(f'/api/stats/push -> HTTP {resp.status}: {body[:100]}')
        c.close()
        sys.exit(0)
    print(f'  Waiting... ({i+1}/10)')

print('FAILED: Port not open after 10s')
