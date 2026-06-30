# -*- coding: utf-8 -*-
"""Restart 5008 (mobile_api_ai app.py) after services/__init__.py fix."""
import subprocess, sys, os, time

PY = r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe'
APP = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\app.py'
LOG_OUT = r'd:\yuan\不锈钢网带跟单3.0\logs\5008.log'

import socket
# 检查端口
def port_in_use(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('127.0.0.1', port))
        s.close()
        return True
    except Exception:
        return False

print('starting 5008 ...')
proc = subprocess.Popen(
    [PY, '-B', APP],
    cwd=r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai',
    creationflags=subprocess.CREATE_NEW_CONSOLE,
    stdout=open(LOG_OUT, 'a', encoding='utf-8'),
    stderr=subprocess.STDOUT,
)
print(f'pid={proc.pid}')
for i in range(20):
    time.sleep(1)
    if port_in_use(5008):
        print(f'5008 up after {i+1}s')
        sys.exit(0)
print('5008 not listening after 20s')
sys.exit(1)
