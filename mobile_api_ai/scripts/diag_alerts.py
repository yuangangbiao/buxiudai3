# -*- coding: utf-8 -*-
"""看 alerts 页内容"""
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
r = op.open(BASE + '/inventory/alerts', timeout=5)
body = r.read().decode('utf-8', errors='replace')
print('GET /inventory/alerts ->', r.status, 'len=', len(body))
Path(r'd:\yuan\alerts_real.html').write_text(body, encoding='utf-8')

import re
rows = re.findall(r'<tr[^>]*class="[^"]*table-danger[^"]*"[^>]*>', body)
print('table-danger 行数:', len(rows))
for kw in ['zero_stock', 'low_stock', 'over_stock', '待处理', '处理', 'badge-warn']:
    print(f'  {kw}: {body.count(kw)}')
# 找 td 内的 product_name (有 tr 包含 table-danger)
trs = re.findall(r'<tr[^>]*>(.*?)</tr>', body, re.DOTALL)
print('总 tr 数:', len(trs))
# 看前 4 个 tr 的前 50 字符
for i, tr in enumerate(trs[:8]):
    text = re.sub(r'<[^>]+>', ' ', tr).strip()
    print(f'  tr{i}: {text[:80]}')
