# -*- coding: utf-8 -*-
"""检查调度中心 5003 启动问题"""
import subprocess
import time
import socket
import sys

PYTHON = r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe'
CWD = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'

print('启动调度中心并捕获输出...')
proc = subprocess.Popen(
    [PYTHON, 'standalone_dispatch_server.py'],
    cwd=CWD,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    creationflags=subprocess.CREATE_NO_WINDOW
)

time.sleep(8)

if proc.poll() is not None:
    # 已退出
    stdout, stderr = proc.communicate()
    print(f'进程已退出 (exit code={proc.returncode})')
    print('\n=== STDOUT ===')
    print(stdout[:3000])
    print('\n=== STDERR ===')
    print(stderr[:3000])
else:
    print(f'进程运行中 (PID={proc.pid})')
    s = socket.socket()
    r = s.connect_ex(('127.0.0.1', 5003))
    if r == 0:
        print('端口5003: ✅ 已监听')
    else:
        print(f'端口5003: ❌ 未就绪 (err={r})')
    s.close()
    proc.terminate()
