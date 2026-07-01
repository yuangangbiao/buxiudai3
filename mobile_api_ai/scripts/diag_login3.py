# -*- coding: utf-8 -*-
"""等待 5010 端口稳定可访问（最多 30 秒），然后测登录"""
import socket
import time
import urllib.request
import urllib.parse
import http.cookiejar

BASE = 'http://127.0.0.1:5010'

# 1) 等待端口 + 等待 HTTP 200 响应
print('[1] 等待服务就绪...')
ready = False
for i in range(30):
    try:
        with socket.create_connection(('127.0.0.1', 5010), timeout=1):
            r = urllib.request.urlopen(BASE + '/login', timeout=2)
            if r.status == 200:
                print(f'  服务就绪 (i={i}s)')
                ready = True
                break
    except Exception:
        time.sleep(1)

if not ready:
    print('  服务未就绪')
    raise SystemExit(1)

# 2) 登录测试
print('[2] 登录测试')
cj = http.cookiejar.CookieJar()

# 关闭自动重定向
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        return fp
opener_no = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NoRedirect())

# 2a) GET /login
r = opener_no.open(BASE + '/login', timeout=5)
print(f'  GET /login -> {r.status}')

# 2b) POST /login
data = urllib.parse.urlencode({'password': 'Admin@2026'}).encode()
req = urllib.request.Request(BASE + '/login', data=data, method='POST')
try:
    r = opener_no.open(req, timeout=5)
    print(f'  POST /login -> {r.status}  Location: {r.headers.get("Location", "(none)")}')
except urllib.error.HTTPError as e:
    print(f'  POST /login -> HTTP {e.code}  Location: {e.headers.get("Location", "(none)")}')
    body = e.read(800).decode('utf-8', errors='replace')
    import re
    for m in re.finditer(r'<div class="alert[^"]*"[^>]*>([^<]+)<', body):
        print(f'  错误提示: {m.group(1).strip()[:150]}')
    for m in re.finditer(r'密码[^<]{0,80}', body):
        print(f'  错误文本: {m.group(0)[:150]}')
