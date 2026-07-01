# -*- coding: utf-8 -*-
"""端到端验证：登录 + 访问 dashboard"""
import urllib.request
import urllib.parse
import http.cookiejar
from pathlib import Path

BASE = 'http://127.0.0.1:5010'
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1) GET /login
r = opener.open(BASE + '/login', timeout=5)
print(f'[1] GET /login -> {r.status}')

# 2) POST /login
data = urllib.parse.urlencode({'password': 'Admin@2026'}).encode()
req = urllib.request.Request(BASE + '/login', data=data, method='POST')
try:
    r = opener.open(req, timeout=5)
    print(f'[2] POST /login -> {r.status}  URL: {r.geturl()[:80]}')
    body = r.read(2000).decode('utf-8', errors='replace')
    Path(r'd:\yuan\dashboard.html').write_text(body, encoding='utf-8')
    print(f'    body saved to d:\\yuan\\dashboard.html (len={len(body)})')
    # 看是否有错误
    for kw in ['错误', '500', 'AttributeError', 'UndefinedError']:
        if kw in body:
            print(f'    ⚠️ body contains: {kw}')
    # 看是否有 dashboard 标志
    for kw in ['库存', 'dashboard', '总商品', '本月入库', '本月出库']:
        if kw in body:
            print(f'    ✅ body contains: {kw}')
            break
except urllib.error.HTTPError as e:
    print(f'[2] POST /login -> HTTP {e.code}')
    body = e.read().decode('utf-8', errors='replace')
    Path(r'd:\yuan\login_err.html').write_text(body, encoding='utf-8')
    print(f'    saved to login_err.html')
