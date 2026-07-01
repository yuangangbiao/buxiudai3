# -*- coding: utf-8 -*-
"""看 POST /login 401 完整 body"""
import urllib.request
import urllib.parse
import http.cookiejar

BASE = 'http://127.0.0.1:5010'
cj = http.cookiejar.CookieJar()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        return fp
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NoRedirect())

# GET /login
r = opener.open(BASE + '/login', timeout=5)
print('Cookies after GET:', [c.name for c in cj])
html_get = r.read().decode('utf-8', errors='replace')

# POST /login
data = urllib.parse.urlencode({'password': 'Admin@2026'}).encode()
req = urllib.request.Request(BASE + '/login', data=data, method='POST')
try:
    r = opener.open(req, timeout=5)
    print(f'POST -> {r.status}')
    body = r.read().decode('utf-8', errors='replace')
    print('---body start---')
    print(body[:2000])
    print('---body end---')
except urllib.error.HTTPError as e:
    print(f'POST -> HTTP {e.code}')
    body = e.read().decode('utf-8', errors='replace')
    print('---body start---')
    print(body[:2000])
    print('---body end---')
    print('---response headers---')
    for k, v in e.headers.items():
        print(f'  {k}: {v}')
