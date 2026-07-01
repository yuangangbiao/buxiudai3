# -*- coding: utf-8 -*-
"""真实 GET 探测所有侧边栏链接的实际状态码"""
import urllib.request
import urllib.parse
import http.cookiejar
from pathlib import Path

BASE = 'http://127.0.0.1:5010'
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(BASE + '/login', timeout=5)
op.open(urllib.request.Request(BASE + '/login',
    data=urllib.parse.urlencode({'password': 'Admin@2026'}).encode(), method='POST'), timeout=5)

sidebar = [
    '/inventory/dashboard', '/inventory/inbound', '/inventory/outbound',
    '/inventory/batch', '/inventory/alerts', '/inventory/stock',
    '/inventory/products', '/inventory/suppliers', '/inventory/categories',
    '/inventory/base', '/inventory/warehouses', '/inventory/stocktake',
    '/inventory/transfer', '/inventory/scanner', '/inventory/reports',
    '/inventory/notifications', '/inventory/backup', '/inventory/export',
    '/inventory/recycle-bin', '/inventory/settings',
]

results = []
for path in sidebar:
    try:
        r = op.open(BASE + path, timeout=5)
        results.append((r.status, path, ''))
    except urllib.error.HTTPError as e:
        body = ''
        try:
            body = e.read(80).decode('utf-8', errors='replace')
        except: pass
        results.append((e.code, path, body[:60]))
    except Exception as e:
        results.append((-1, path, str(e)[:60]))

lines = ['=== 侧边栏链接实际状态 ===', '']
ok, fail = [], []
for status, path, body in sorted(results, key=lambda x: (x[0], x[1])):
    mark = '✅' if status == 200 else '❌'
    line = f'{mark} [{status}] {path}'
    if body and status != 200:
        line += f'  body: {body}'
    lines.append(line)
    if status == 200:
        ok.append(path)
    else:
        fail.append((status, path))

text = '\n'.join(lines)
Path(r'd:\yuan\sidebar_real.txt').write_text(text, encoding='utf-8')
print(text)
print()
print(f'✅ 正常: {len(ok)}  ❌ 失败: {len(fail)}')
