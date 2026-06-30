# -*- coding: utf-8 -*-
"""启动 8008 sync_bridge + 5008 移动报工 API，并验证就绪"""
import os
import sys
import time
import subprocess
import urllib.request
import urllib.error

# 强制 UTF-8 输出
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

PY = r'C:\Users\lenovo\AppData\Local\Python\bin\python3.14-64.exe'
CWD = r'd:\yuan\不锈钢网带跟单3.0'
MOBILE_API_DIR = os.path.join(CWD, 'mobile_api_ai')

LOGS_DIR = os.path.join(CWD, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)


def kill_existing(port: int):
    """杀掉指定端口的旧进程"""
    print(f'[1/4] 清理 {port} 端口旧进程...')
    try:
        out = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             f'Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | '
             f'Select-Object -ExpandProperty OwningProcess'],
            capture_output=True, text=True, timeout=10
        )
        pids = [int(x) for x in out.stdout.split() if x.strip().isdigit()]
        for pid in pids:
            subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                           capture_output=True, timeout=5)
            print(f'  killed pid={pid}')
    except Exception as e:
        print(f'  cleanup warn: {e}')


def start_service(name: str, script: str, port: int, log_file: str):
    """启动一个服务（detach）"""
    log_path = os.path.join(LOGS_DIR, log_file)
    print(f'[2/4] 启动 {name} (端口 {port})... log={log_file}')
    log_fp = open(log_path, 'ab', buffering=0)
    proc = subprocess.Popen(
        [PY, script],
        cwd=MOBILE_API_DIR,
        stdout=log_fp,
        stderr=log_fp,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
    )
    print(f'  PID={proc.pid}')
    return proc


def wait_ready(port: int, path: str = '/api/health', timeout: int = 60):
    """等待端口就绪"""
    print(f'[3/4] 等待端口 {port} 就绪...')
    for i in range(timeout):
        time.sleep(1)
        try:
            r = urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=3)
            body = r.read()[:200].decode('utf-8', errors='replace')
            print(f'  READY at {i+1}s  status={r.status}  body={body[:120]}')
            return True
        except urllib.error.HTTPError as e:
            if e.code in (404, 401):
                # 服务在跑，只是端点不同
                print(f'  ALIVE at {i+1}s  status={e.code} (端点可能不同)')
                return True
        except Exception as e:
            if i % 5 == 4:
                print(f'  waiting {i+1}s... {type(e).__name__}')
    return False


def health_check():
    """全服务健康检查"""
    print('[4/4] 全服务健康检查')
    targets = [
        (5001, '/api/orders', '5001 desktop_web'),
        (5003, '/api/dispatch-center/health', '5003 dispatch'),
        (5008, '/api/health', '5008 mobile_api'),
        (8008, '/health', '8008 sync_bridge'),
    ]
    for port, path, name in targets:
        try:
            r = urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=5)
            body = r.read()[:200].decode('utf-8', errors='replace')
            print(f'  ✅ {name:25s} {r.status}  {body[:100]}')
        except urllib.error.HTTPError as e:
            print(f'  ⚠️  {name:25s} {e.code}  (服务在跑，端点可能不同)')
        except Exception as e:
            print(f'  ❌ {name:25s}  DOWN  {type(e).__name__}')


if __name__ == '__main__':
    # 1. 清理旧进程
    kill_existing(5008)
    kill_existing(8008)

    # 2. 启动 8008 sync_bridge
    start_service('8008 sync_bridge', 'sync_bridge_server.py', 8008, '8008.log')

    # 3. 启动 5008 移动报工 API
    start_service('5008 mobile_api', 'app.py', 5008, '5008.log')

    # 4. 等待就绪
    ready_8008 = wait_ready(8008, '/api/health', timeout=60)
    ready_5008 = wait_ready(5008, '/api/health', timeout=60)

    # 5. 健康检查
    health_check()

    print()
    print('=' * 60)
    print(f'8008 sync_bridge:  {"✅ READY" if ready_8008 else "❌ TIMEOUT"}')
    print(f'5008 mobile_api:   {"✅ READY" if ready_5008 else "❌ TIMEOUT"}')
    print('=' * 60)
    print('日志:')
    print('  - d:\\yuan\\不锈钢网带跟单3.0\\logs\\8008.log')
    print('  - d:\\yuan\\不锈钢网带跟单3.0\\logs\\5008.log')
