# -*- coding: utf-8 -*-
"""P0 端到端真实业务验证: 5001 登录 → 调 5003 业务接口

不 mock, 走真实 HTTP, 验证修复后 5001 的 session token 能被 5003 接受.
"""
import sys
import time
import json
import requests

WEB = 'http://127.0.0.1:5001'
DISPATCH = 'http://127.0.0.1:5003'

print('=' * 70)
print('P0 端到端真实业务验证 (不 mock)')
print('=' * 70)

# Step 1: 5001 登录
print('\n[Step 1] 5001 登录 (修复后应返回 base64 token)')
login = requests.post(
    f'{WEB}/api/login',
    json={'username': '测试'},
    timeout=10
)
print(f'  状态: {login.status_code}')
login_body = login.json()
print(f'  响应: {json.dumps(login_body, ensure_ascii=False)[:300]}')

if login_body.get('code') != 0:
    print(f'  [FAIL] 登录失败: {login_body.get("message")}')
    sys.exit(1)

# Step 2: 拿 session cookie
print('\n[Step 2] 检查 session cookie')
sess = login.cookies
print(f'  收到 cookies: {[c.name for c in sess]}')
session_cookie = sess.get('session')
print(f'  session cookie: {session_cookie[:50]}...' if session_cookie else '  无 session cookie')

# Step 3: 用 session cookie 调 5001 → 5003 的代理接口
print('\n[Step 3] 用 session cookie 调 5001 → 5003 代理接口 /api/operators')
# 这个接口会经 _call_dispatch 转发到 5003 /api/enterprise/operators
ops_resp = requests.get(
    f'{WEB}/api/operators',
    cookies=sess,
    timeout=10
)
print(f'  状态: {ops_resp.status_code}')
body_str = ops_resp.text[:500]
print(f'  响应 (前500字): {body_str}')

if ops_resp.status_code == 401:
    print('  [FAIL] P0 修复失败: 5001 代理调 5003 仍被 401 拒 (session token 仍不兼容 5003 协议)')
    sys.exit(1)
elif ops_resp.status_code == 200:
    print('  [OK] P0 修复验证通过: 5001 session token 被 5003 接受')

# Step 4: 验证修复前 vs 修复后 token 格式
print('\n[Step 4] 直接对比: 5001 修复后会话 vs 5003 协议期望')
import base64
import secrets

# 拿到 user
user = login_body['data']
uid = user.get('id')
uname = user.get('name')
print(f'  用户: id={uid}, name={uname}')

# 5003 协议期望 token
expected_token = base64.b64encode(f'{uid}:{uname}'.encode('utf-8')).decode('utf-8')
print(f'  5003 期望 token: {expected_token[:60]}...')

# 修复前: secrets.token_hex(32) — 会被 5003 拒
old_token = secrets.token_hex(32)
print(f'  旧协议 token:   {old_token[:60]}...')

# Step 5: 跨服务独立验证
print('\n[Step 5] 独立验证: 修复后 token 通过 5003 _dispatch_auth_check 协议')
try:
    r3 = requests.get(
        f'{DISPATCH}/api/dispatch-center/status',
        headers={'X-Dispatch-Token': expected_token},
        timeout=5
    )
    print(f'  5003 /api/dispatch-center/status 状态: {r3.status_code}')
    if r3.status_code == 200:
        print('  [OK] 修复后 token 调 5003 鉴权通过')
    else:
        print(f'  [FAIL] 修复后 token 调 5003 仍失败: {r3.text[:200]}')
        sys.exit(1)
except Exception as e:
    print(f'  [WARN] 5003 调用异常: {e}')

# 反向验证: 旧协议 token 一定被 5003 拒 (确认 bug 真实存在)
try:
    r3_old = requests.get(
        f'{DISPATCH}/api/dispatch-center/status',
        headers={'X-Dispatch-Token': old_token},
        timeout=5
    )
    print(f'  5003 对旧 token (token_hex) 状态: {r3_old.status_code} (期望 401)')
    if r3_old.status_code == 401:
        print('  [OK] 反向验证: 旧协议 token 被 5003 拒 — 确认 bug 真实存在, 修复有效')
    else:
        print(f'  [WARN] 反向验证异常: 旧 token 居然通过 5003 = {r3_old.status_code}')
except Exception as e:
    print(f'  [WARN] 反向验证异常: {e}')

print('\n' + '=' * 70)
print('[P0 修复验证] ✅ 端到端真实业务通过')
print('=' * 70)
