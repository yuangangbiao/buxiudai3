# -*- coding: utf-8 -*-
"""测 5 个新页面"""
import urllib.request
import urllib.parse
import http.cookiejar
from pathlib import Path

BASE = 'http://127.0.0.1:5010'
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 登录
op.open(BASE + '/login', timeout=5)
op.open(urllib.request.Request(BASE + '/login',
    data=urllib.parse.urlencode({'password': 'Admin@2026'}).encode(), method='POST'), timeout=5)

results = []
for path in ['/inventory/warehouses', '/inventory/categories', '/inventory/export',
             '/inventory/base', '/inventory/settings']:
    try:
        r = op.open(BASE + path, timeout=5)
        body = r.read().decode('utf-8', errors='replace')
        results.append(f'[{r.status}] {path} len={len(body)}')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:100]
        results.append(f'[{e.code}] {path} {body}')
    except Exception as e:
        results.append(f'[ERR] {path} {e}')

text = '\n'.join(results)
Path(r'd:\yuan\diag_5pages.txt').write_text(text, encoding='utf-8')
print(text)
