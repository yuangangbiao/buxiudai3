# -*- coding: utf-8 -*-
"""登录后访问 dashboard，记录真实响应大小和状态"""
import urllib.request
import urllib.parse
import http.cookiejar
from pathlib import Path

BASE = 'http://127.0.0.1:5010'
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1) GET /login
r = opener.open(BASE + '/login', timeout=5)
print(f'GET /login -> {r.status}')

# 2) POST /login
data = urllib.parse.urlencode({'password': 'Admin@2026'}).encode()
req = urllib.request.Request(BASE + '/login', data=data, method='POST')
r = opener.open(req, timeout=5)
print(f'POST /login -> {r.status}  URL: {r.geturl()[:80]}')

# 3) GET /inventory/dashboard
try:
    r = opener.open(BASE + '/inventory/dashboard', timeout=10)
    body = r.read()
    print(f'GET /inventory/dashboard -> {r.status}  len={len(body)}')
    Path(r'd:\yuan\dashboard_real.html').write_bytes(body)
    print(f'Saved to d:\\yuan\\dashboard_real.html')

    # 检查是否有 Jinja 错误
    if 'Traceback' in body.decode('utf-8', errors='replace'):
        print('⚠️ body contains Traceback')
    if 'UndefinedError' in body.decode('utf-8', errors='replace'):
        print('⚠️ UndefinedError detected')
    # 找 "卡" 错误
    body_text = body.decode('utf-8', errors='replace')
    if '数据加载失败' in body_text or '加载失败' in body_text:
        print('⚠️ 数据加载失败 in body')
except urllib.error.HTTPError as e:
    print(f'GET /inventory/dashboard -> HTTP {e.code}')
    body = e.read()
    Path(r'd:\yuan\dashboard_err.html').write_bytes(body)
    print(f'len={len(body)}, saved to d:\\yuan\\dashboard_err.html')
    print('---body---')
    print(body.decode('utf-8', errors='replace')[:2000])
