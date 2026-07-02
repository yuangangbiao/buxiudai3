# -*- coding: utf-8 -*-
"""
等待服务就绪脚本（跨平台版）

用法: python ci/wait_service.py <port> <url> <timeout>
功能:
1. 用 socket 检测端口是否监听（跨平台，不依赖 HTTP 响应码）
2. 端口就绪后尝试验证 HTTP 服务健康
3. 即使无 HTTP 响应，端口监听即认为就绪
"""
import sys
import time
import socket
import urllib.request
import urllib.error
import re

if len(sys.argv) < 4:
    print(f"用法: {sys.argv[0]} <port> <url> <timeout>")
    sys.exit(1)

port = sys.argv[1]
url = sys.argv[2]
timeout = int(sys.argv[3])

match = re.search(r'http[s]?://([^/:]+)', url)
host = match.group(1) if match else '127.0.0.1'

print(f"[wait_service] 等待 {host}:{port} 就绪, timeout={timeout}s...")


def is_port_listening(host, port_str):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, int(port_str)))
        sock.close()
        return result == 0
    except Exception:
        return False


# 阶段1: 等待端口监听
start = time.time()
while time.time() - start < timeout:
    elapsed = time.time() - start
    if is_port_listening(host, port):
        print(f"[wait_service] ✅ 端口 {port} 已监听 ({elapsed:.1f}s)")
        break
    print(f"[wait_service] 端口 {port} 未监听 ({elapsed:.0f}s/{timeout}s)...")
    time.sleep(2)
else:
    print(f"[wait_service] ❌ 端口 {port} 在 {timeout}s 内未监听")
    sys.exit(1)

# 阶段2: 尝试 HTTP 验证（最多15s）
http_timeout = 15
print(f"[wait_service] 阶段2: HTTP验证, timeout={http_timeout}s...")
http_start = time.time()

while time.time() - http_start < http_timeout:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode('utf-8', errors='replace')[:80]
            print(f"[wait_service] ✅ HTTP {resp.status} - {body[:50]!r}")
            sys.exit(0)
    except urllib.error.HTTPError as e:
        print(f"[wait_service] ✅ HTTP {e.code} (服务已响应)")
        sys.exit(0)
    except (urllib.error.URLError, ConnectionRefusedError):
        pass
    except Exception as e:
        pass

    time.sleep(1)

print(f"[wait_service] ⚠ 无HTTP响应，但端口已监听，视为就绪")
sys.exit(0)
