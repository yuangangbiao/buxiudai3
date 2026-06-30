# -*- coding: utf-8 -*-
"""重启 5001 desktop_web server (P0 修复 验证用)

按 workspace rule: 用 Python 脚本管理进程, 不用 PowerShell & 连接符
"""
import subprocess
import sys
import time
import os
import signal

PID_TO_KILL = 16176  # 当前 5001 进程
SCRIPT_PATH = r'd:\yuan\不锈钢网带跟单3.0\desktop_web\server.py'
PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
PYTHON_EXE = r'C:\Users\lenovo\AppData\Local\Python\bin\python3.14-64.exe'
# 注意: 5001 是用 bin\python3.14-64.exe 启动的, 不是 pythoncore, 必须用相同的解释器

# 1) 杀老进程
print(f'[RESTART 5001] 杀 PID {PID_TO_KILL} ...')
try:
    subprocess.run(['taskkill', '/PID', str(PID_TO_KILL), '/F'], check=False)
    time.sleep(2)
except Exception as e:
    print(f'[WARN] kill 失败: {e}')

# 2) 启动新进程
print(f'[RESTART 5001] 启动新进程 ...')
creationflags = 0
if sys.platform == 'win32':
    creationflags = subprocess.CREATE_NEW_CONSOLE

new_proc = subprocess.Popen(
    [PYTHON_EXE, SCRIPT_PATH],
    cwd=PROJECT_ROOT,
    creationflags=creationflags,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
print(f'[RESTART 5001] 新进程 PID: {new_proc.pid}')

# 3) 等服务起来
time.sleep(3)

# 4) 健康检查
import urllib.request
import urllib.error
try:
    r = urllib.request.urlopen('http://127.0.0.1:5001/api/enterprise/operators', timeout=5)
    print(f'[RESTART 5001] 健康检查: 状态 {r.status} (期望 401 = 服务起来了)')
except urllib.error.HTTPError as e:
    if e.code == 401:
        print(f'[RESTART 5001] 健康检查 OK: 状态 401 (服务正常, 鉴权按预期拒绝)')
    else:
        print(f'[RESTART 5001] 健康检查异常: HTTP {e.code}')
        sys.exit(1)
except Exception as e:
    print(f'[RESTART 5001] 健康检查失败: {e}')
    sys.exit(1)

print('[RESTART 5001] 完成')
