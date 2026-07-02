# -*- coding: utf-8 -*-
"""
[v3.6] CI-8008 检查脚本

检查 mobile_api_ai/sync_bridge_server.py (8008) 能正常启动:
1. 8008 服务能启动（端口 8008 监听）
2. /health 或根路径返回 200

前置条件:
- MySQL 已启动 (CI 提供 mysql:8.0 容器)
- 5003 调度中心已启动 (standalone_dispatch_server.py)
"""
import os
import sys
import time
import urllib.request
import urllib.error

PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())
os.chdir(PROJECT_ROOT)

PORT_8008 = 8008
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '88888888')
DB_NAME = os.getenv('DB_NAME', 'container_center')

def check_port(port, timeout=60):
    url = f"http://127.0.0.1:{port}/"
    for i in range(timeout):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                code = resp.status
                print(f"  [{i+1}s] GET {url} -> {code}")
                if code == 200:
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  [{i+1}s] GET {url} -> 404 (server is up)")
                return True
            print(f"  [{i+1}s] GET {url} -> {e.code}")
        except Exception as e:
            print(f"  [{i+1}s] Waiting... ({e})")
        time.sleep(1)
    return False

def main():
    print(f"[CI-8008] Checking sync_bridge_server.py on port {PORT_8008}...")
    ok = check_port(PORT_8008, timeout=60)
    if ok:
        print(f"[CI-8008] PASS: Server on port {PORT_8008} is responding")
        sys.exit(0)
    else:
        print(f"[CI-8008] FAIL: Server on port {PORT_8008} did not respond")
        sys.exit(1)

if __name__ == '__main__':
    main()
