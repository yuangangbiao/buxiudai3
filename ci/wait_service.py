# -*- coding: utf-8 -*-
"""
等待服务就绪脚本

用法: python ci/wait_service.py <port> <url> <timeout>
"""
import sys
import time
import urllib.request
import urllib.error

if len(sys.argv) < 4:
    print(f"用法: {sys.argv[0]} <port> <url> <timeout>")
    sys.exit(1)

port = sys.argv[1]
url = sys.argv[2]
timeout = int(sys.argv[3])

print(f"[wait_service] 等待 {port} ({url}) 就绪, 超时 {timeout}s...")

start = time.time()
while time.time() - start < timeout:
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            elapsed = time.time() - start
            print(f"[wait_service] ✅ {port} 已就绪 ({elapsed:.1f}s) - HTTP {resp.status}")
            sys.exit(0)
    except urllib.error.HTTPError as e:
        if e.code in (200, 401, 403):
            elapsed = time.time() - start
            print(f"[wait_service] ✅ {port} 已就绪 ({elapsed:.1f}s) - HTTP {e.code}")
            sys.exit(0)
        print(f"[wait_service] {port} 返回 HTTP {e.code}, 重试...")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[wait_service] {port} 未就绪 ({elapsed:.0f}s): {type(e).__name__}")

    time.sleep(1)

print(f"[wait_service] ❌ {port} 在 {timeout}s 内未就绪")
sys.exit(1)
