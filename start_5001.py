# -*- coding: utf-8 -*-
"""
启动 desktop_web (5001 端口)

架构: desktop_web/server.py - 桌面 Web 化服务
按小袁"渐进式 Web 化"决策(2026-06-22),只读 core/ + models/ + 复用 5003 API

启动: python start_5001.py
访问: http://localhost:5001
"""
import os
import sys
import time
import subprocess
from pathlib import Path

PYTHON = sys.executable
WORK_DIR = Path(__file__).parent.resolve()
SCRIPT = WORK_DIR / 'desktop_web' / 'server.py'
LOG = WORK_DIR / 'logs' / '5001.log'
LOG.parent.mkdir(parents=True, exist_ok=True)

def load_env():
    env_file = WORK_DIR / '.env'
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

def kill_5001():
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue | "
         "Stop-Process -Force -ErrorAction SilentlyContinue"],
        capture_output=True, text=True, timeout=15
    )
    print('[start_5001] 清理旧 5001 进程...')

def start():
    print('=' * 60)
    print('[start_5001] 启动 desktop_web (5001)...')
    print('=' * 60)

    kill_5001()
    load_env()

    os.environ['DESKTOP_WEB_PORT'] = '5001'
    os.environ.setdefault('JWT_SECRET_KEY', os.environ.get('JWT_SECRET_KEY', 'dev-secret-key-do-not-use-in-prod'))

    log_fp = open(LOG, 'ab', buffering=0)

    proc = subprocess.Popen(
        [PYTHON, str(SCRIPT)],
        cwd=str(WORK_DIR),
        stdout=log_fp,
        stderr=log_fp,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0,
    )
    print(f'[start_5001] PID={proc.pid}')

    for i in range(20):
        time.sleep(1)
        try:
            import urllib.request
            r = urllib.request.urlopen('http://localhost:5001/api/health', timeout=2)
            print(f'[start_5001] ✅ READY at {i+1}s, status={r.status}')
            return
        except Exception as e:
            if i % 5 == 4:
                print(f'[start_5001] waiting {i+1}s... last error: {type(e).__name__}')

    print(f'[start_5001] ⚠️  5001 未响应，请检查 {LOG}')

if __name__ == '__main__':
    start()
