# -*- coding: utf-8 -*-
"""完整诊断：取 401 页面正文、确认 .env、确认进程启动时间"""
import socket
import time
import urllib.request
import urllib.parse
import http.cookiejar
import subprocess
from pathlib import Path

BASE = 'http://127.0.0.1:5010'
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1) .env 第 5 行
env_path = Path(r'd:\yuan\不锈钢网带跟单3.0\.env')
line5 = env_path.read_text(encoding='utf-8').splitlines()[4]
print('[.env 第 5 行]')
print(' ', line5)
print()

# 2) 当前 5010 进程启动时间
out = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True, shell=True).stdout
pid_5010 = None
for line in out.splitlines():
    if ':5010' in line and 'LISTENING' in line:
        parts = line.strip().split()
        if parts and parts[-1].isdigit():
            pid_5010 = int(parts[-1])
            break
print(f'[5010 进程] PID={pid_5010}')

# 3) 重新 POST /login 并打印完整 401 body
print('[POST /login]')
r = opener.open(BASE + '/login', timeout=5)
login_html = r.read().decode('utf-8', errors='replace')

import re
csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_html)
csrf_val = csrf.group(1) if csrf else None
print(f'  GET /login CSRF: {csrf_val[:24] + "..." if csrf_val else "NONE"}')

data = urllib.parse.urlencode({
    'password': 'Admin@2026',
    **({'csrf_token': csrf_val} if csrf_val else {})
}).encode()
req = urllib.request.Request(BASE + '/login', data=data, method='POST')
try:
    r = opener.open(req, timeout=5)
    print(f'  状态: {r.status}  (意外 2xx)')
except urllib.error.HTTPError as e:
    print(f'  状态: HTTP {e.code}')
    body = e.read().decode('utf-8', errors='replace')
    # 找错误信息
    for m in re.finditer(r'(?:error|提示|alert)[^<]{0,200}', body, re.IGNORECASE):
        print(f'  body片段: {m.group(0)[:150]}')
    # 找 <p class=...> 或 <div class="error">
    for m in re.finditer(r'<(?:p|div|span)[^>]*>([^<]{2,200})</', body):
        text = m.group(1).strip()
        if text and text not in ('库存管理登录',):
            print(f'  body元素: {text[:150]}')
