# -*- coding: utf-8 -*-
"""端到端验证：等待重启 + 登录 + dashboard 跳转"""
import socket
import time
import urllib.request
import urllib.parse
import http.cookiejar

BASE = 'http://127.0.0.1:5010'
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1) 等待端口恢复
print('[1] 等待 5010 端口恢复...')
for i in range(20):
    try:
        with socket.create_connection(('127.0.0.1', 5010), timeout=1):
            print(f'  端口就绪 (等待 {i}s)')
            break
    except OSError:
        time.sleep(1)
else:
    print('  ❌ 端口未恢复')
    raise SystemExit(1)

# 2) GET /login 拿 CSRF token（如果有）
print('[2] GET /login ...')
r = opener.open(BASE + '/login', timeout=5)
print(f'  状态: {r.status}')
login_html = r.read().decode('utf-8', errors='replace')
import re
csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_html)
csrf_val = csrf.group(1) if csrf else None
print(f'  CSRF: {csrf_val[:16] + "..." if csrf_val else "NONE"}')

# 3) POST /login 用 Admin@2026
print('[3] POST /login (password=Admin@2026) ...')
data = urllib.parse.urlencode({
    'password': 'Admin@2026',
    **({'csrf_token': csrf_val} if csrf_val else {})
}).encode()
req = urllib.request.Request(BASE + '/login', data=data, method='POST')
try:
    r = opener.open(req, timeout=5)
    print(f'  状态: {r.status}')
    print(f'  URL : {r.geturl()}')
    body = r.read(300).decode('utf-8', errors='replace')
    print(f'  头部: {body[:200]}')
except urllib.error.HTTPError as e:
    print(f'  状态: HTTP {e.code}')
    body = e.read(300).decode('utf-8', errors='replace')
    print(f'  头部: {body[:200]}')

# 4) 跟进 /inventory/dashboard
print('[4] GET /inventory/dashboard (用登录 session) ...')
try:
    r = opener.open(BASE + '/inventory/dashboard', timeout=5)
    print(f'  状态: {r.status} ✅')
except urllib.error.HTTPError as e:
    print(f'  状态: HTTP {e.code} ❌')
    body = e.read(500).decode('utf-8', errors='replace')
    print(f'  body: {body[:500]}')
