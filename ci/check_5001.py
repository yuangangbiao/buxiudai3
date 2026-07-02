# -*- coding: utf-8 -*-
"""
[v3.6] CI-5001 检查脚本

检查 desktop_web (5001) 能正常启动:
1. 5001 服务能启动（端口 5001 监听）
2. /health 健康检查返回 200
3. 核心 API 可访问（/api/orders/list, /api/kanban/list 等）

前置条件:
- MySQL 已启动 (CI 提供 mysql:8.0 容器)
- 5003 调度中心已启动 (standalone_dispatch_server.py)
"""
import os
import sys
import time
import subprocess
import urllib.request
import urllib.error
import signal

PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())
os.chdir(PROJECT_ROOT)

PORT_5001 = 5001
PORT_5003 = 5003
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '88888888')
DB_NAME = os.getenv('DB_NAME', 'container_center')


class C:
    G = '\033[92m'
    R = '\033[91m'
    Y = '\033[93m'
    B = '\033[94m'
    E = '\033[0m'


def passed(name, details=''):
    print(f'{C.G}[PASS]{C.E} {name}')
    if details:
        print(f'       {details}')


def failed(name, details=''):
    print(f'{C.R}[FAIL]{C.E} {name}')
    if details:
        print(f'       {details}')


def http_get(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
            return resp.status, data.decode('utf-8', errors='replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')
    except Exception as e:
        return 0, str(e)


def wait_for_port(port, timeout=30, interval=1):
    """等待端口开始监听"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def check_5001_file():
    """检查 desktop_web/server.py 存在"""
    print(f'\n{C.B}[1/5] 检查 desktop_web/server.py 存在{C.E}')
    path = os.path.join(PROJECT_ROOT, 'desktop_web', 'server.py')
    if not os.path.exists(path):
        failed('desktop_web/server.py', '文件不存在')
        return False
    passed('desktop_web/server.py', f'文件存在 ({os.path.getsize(path)} bytes)')
    return True


def check_5003_running():
    """检查 5003 调度中心是否运行"""
    print(f'\n{C.B}[2/5] 检查 5003 调度中心{C.E}')
    status, body = http_get(f'http://127.0.0.1:{PORT_5003}/health', timeout=3)
    if status == 200:
        passed('5003 调度中心', '运行中')
        return True
    failed('5003 调度中心', f'HTTP {status}')
    return False


def check_5001_startup():
    """启动 5001 并等待就绪"""
    print(f'\n{C.B}[3/5] 启动 5001 desktop_web{C.E}')
    env = os.environ.copy()
    env['DESKTOP_WEB_PORT'] = str(PORT_5001)
    env['DISPATCH_BASE'] = f'http://127.0.0.1:{PORT_5003}'
    env['JWT_SECRET_KEY'] = 'ci_test_secret_key_for_5001_health_check'
    env['DB_HOST'] = DB_HOST
    env['DB_PORT'] = str(DB_PORT)
    env['DB_USER'] = DB_USER
    env['DB_PASSWORD'] = DB_PASSWORD
    env['DB_NAME'] = DB_NAME

    script = os.path.join(PROJECT_ROOT, 'desktop_web', 'server.py')

    try:
        proc = subprocess.Popen(
            [sys.executable, script],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=PROJECT_ROOT,
        )
    except Exception as e:
        failed('启动 5001', f'异常: {e}')
        return None

    print(f'       进程 PID={proc.pid}, 等待端口 {PORT_5001} 就绪...')

    if not wait_for_port(PORT_5001, timeout=30):
        proc.kill()
        try:
            stdout, stderr = proc.communicate(timeout=5)
            out = stdout.decode('utf-8', errors='replace')[-500:]
            err = stderr.decode('utf-8', errors='replace')[-500:]
            print(f'       STDOUT: {out}')
            print(f'       STDERR: {err}')
        except Exception:
            pass
        failed('5001 启动', f'端口 {PORT_5001} 30s 内未就绪')
        return None

    passed('5001 启动', f'端口 {PORT_5001} 已监听')
    return proc


def check_5001_health(proc):
    """健康检查 + 核心 API"""
    print(f'\n{C.B}[4/5] 健康检查 + 核心 API{C.E}')

    checks = [
        ('/health', 200),
        ('/api/orders/list', (200, 401)),
        ('/api/orders/product-types', (200,)),
        ('/api/operators', (200, 401)),
        ('/api/kanban/list', (200, 401)),
    ]

    results = []
    for path, expected_codes in checks:
        url = f'http://127.0.0.1:{PORT_5001}{path}'
        status, body = http_get(url, timeout=5)
        ok = status in (expected_codes if isinstance(expected_codes, tuple) else (expected_codes,))
        results.append((path, status, ok))
        marker = f'{C.G}✅{C.E}' if ok else f'{C.R}❌{C.E}'
        print(f'       {marker} {path} -> HTTP {status}')

    all_ok = all(r[2] for r in results)
    if all_ok:
        passed('API 健康', f'{len(checks)}/{len(checks)} 端点可访问')
    else:
        failed('API 健康', f'{sum(r[2] for r in results)}/{len(checks)} 端点可访问')
        for path, status, ok in results:
            if not ok:
                print(f'       ❌ {path} 返回 HTTP {status}')

    return all_ok


def cleanup(proc):
    """停止 5001 进程"""
    print(f'\n{C.B}[5/5] 停止 5001{C.E}')
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=5)
            passed('停止 5001', f'进程已终止')
        except subprocess.TimeoutExpired:
            proc.kill()
            passed('停止 5001', f'进程已强制终止')
        except Exception as e:
            print(f'       停止进程异常: {e}')
    else:
        print('       无进程需要停止')


def main():
    print(f'{C.B}{"="*60}{C.E}')
    print(f'{C.B}  CI-5001 检查：desktop_web (5001) 启动验证{C.E}')
    print(f'{C.B}{"="*60}{C.E}')

    proc = None
    try:
        if not check_5001_file():
            return 1

        if not check_5003_running():
            print(f'{C.Y}       警告: 5003 未运行, 5001 部分功能受限{C.E}')

        proc = check_5001_startup()
        if proc is None:
            return 1

        health_ok = check_5001_health(proc)

        print(f'\n{C.B}{"="*60}{C.E}')
        print(f'{C.B}  CI-5001 检查结果汇总{C.E}')
        print(f'{C.B}{"="*60}{C.E}')

        if health_ok:
            print(f'\n{C.G}{"="*60}{C.E}')
            print(f'{C.G}  ✅ CI-5001 全部通过 - desktop_web 健康{C.E}')
            print(f'{C.G}{"="*60}{C.E}')
            return 0
        else:
            print(f'\n{C.R}❌ CI-5001 部分失败{C.E}')
            return 1
    finally:
        cleanup(proc)


if __name__ == '__main__':
    sys.exit(main())
