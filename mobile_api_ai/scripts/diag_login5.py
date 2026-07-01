# -*- coding: utf-8 -*-
"""POST /login 401 body 写入文件"""
import urllib.request
import urllib.parse
import http.cookiejar
from pathlib import Path

BASE = 'http://127.0.0.1:5010'
cj = http.cookiejar.CookieJar()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        return fp
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NoRedirect())

# GET
r = opener.open(BASE + '/login', timeout=5)
print('GET status:', r.status)

# POST
data = urllib.parse.urlencode({'password': 'Admin@2026'}).encode()
req = urllib.request.Request(BASE + '/login', data=data, method='POST')
out = Path(r'd:\yuan\login_401.html')
try:
    r = opener.open(req, timeout=5)
    out.write_bytes(r.read())
    print('POST -> 2xx:', r.status)
except urllib.error.HTTPError as e:
    out.write_bytes(e.read())
    print(f'POST -> {e.code}')
    print('Saved to:', out)
    print('Headers:')
    for k, v in e.headers.items():
        print(f'  {k}: {v[:100]}')
