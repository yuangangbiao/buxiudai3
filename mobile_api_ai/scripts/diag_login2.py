# -*- coding: utf-8 -*-
"""远程验证：直接 POST 给 /login，看返回是否 302 (重定向到 dashboard = 登录成功)"""
import socket
import time
import urllib.request
import urllib.parse
import http.cookiejar
import re

BASE = 'http://127.0.0.1:5010'
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj),
                                     urllib.request.HTTPRedirectHandler())

# 关闭自动重定向（自己看 302）
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        return fp
opener2 = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NoRedirect())

# 1) GET /login 取 CSRF
r = opener2.open(BASE + '/login', timeout=5)
html = r.read().decode('utf-8', errors='replace')
m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
csrf = m.group(1) if m else None
print(f'CSRF: {"yes" if csrf else "no"}')

# 2) POST /login (不自动重定向)
data = urllib.parse.urlencode({
    'password': 'Admin@2026',
    **({'csrf_token': csrf} if csrf else {})
}).encode()
req = urllib.request.Request(BASE + '/login', data=data, method='POST')
try:
    r = opener2.open(req, timeout=5)
    print(f'POST 状态: {r.status}')
    print(f'Location: {r.headers.get("Location", "(none)")}')
    body = r.read(800).decode('utf-8', errors='replace')
    # 找错误/提示
    for m in re.finditer(r'<(?:p|div|span)[^>]*class="[^"]*(?:error|alert|warning)[^"]*"[^>]*>([^<]+)<', body, re.IGNORECASE):
        print(f'错误元素: {m.group(1)[:120]}')
except urllib.error.HTTPError as e:
    print(f'POST 状态: HTTP {e.code}')
    body = e.read(800).decode('utf-8', errors='replace')
    for m in re.finditer(r'<(?:p|div|span)[^>]*class="[^"]*(?:error|alert|warning)[^"]*"[^>]*>([^<]+)<', body, re.IGNORECASE):
        print(f'错误元素: {m.group(1)[:120]}')
