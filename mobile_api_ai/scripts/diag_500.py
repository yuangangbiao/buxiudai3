# -*- coding: utf-8 -*-
"""访问 dashboard，抓所有子请求找 500 来源"""
import re
import urllib.request
import urllib.parse
import http.cookiejar
from pathlib import Path

BASE = 'http://127.0.0.1:5010'
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 登录
r = opener.open(BASE + '/login', timeout=5)
data = urllib.parse.urlencode({'password': 'Admin@2026'}).encode()
opener.open(urllib.request.Request(BASE + '/login', data=data, method='POST'), timeout=5)

# 访问 dashboard 拿 body
r = opener.open(BASE + '/inventory/dashboard', timeout=10)
body = r.read().decode('utf-8', errors='replace')
Path(r'd:\yuan\dash_with_500.html').write_text(body, encoding='utf-8')

# 提取所有 /static/ 和 /api/ 资源
urls = set()
for m in re.finditer(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', body):
    url = m.group(1)
    if url.startswith('/'):
        urls.add(url)
    elif url.startswith('http'):
        urls.add(url)
    else:
        urls.add('/' + url)

# 抓 fetch/XHR 调用的 API
for m in re.finditer(r'["\']/(inventory[^"\']*|api[^"\']*)["\']', body):
    urls.add('/' + m.group(1))

print(f'发现 {len(urls)} 个 URL，开始探测...')
print()
errors = []
for url in sorted(urls):
    full = url if url.startswith('http') else BASE + url
    try:
        req = urllib.request.Request(full, method='GET')
        resp = opener.open(req, timeout=5)
        if resp.status >= 400:
            errors.append(f'  ❌ {resp.status} {url}')
        else:
            print(f'  ✓ {resp.status} {url[:60]}')
    except urllib.error.HTTPError as e:
        errors.append(f'  ❌ {e.code} {url}')
        if e.code == 500:
            try:
                err_body = e.read(500).decode('utf-8', errors='replace')
                errors.append(f'      body: {err_body[:300]}')
            except: pass
    except Exception as e:
        errors.append(f'  ⚠️ {url}: {e}')

if errors:
    text = '\n'.join(str(e) for e in errors)
    Path(r'd:\yuan\diag_500_errors.txt').write_text(text, encoding='utf-8')
    print('=== 错误汇总（写入 diag_500_errors.txt）===')
else:
    print('OK')
