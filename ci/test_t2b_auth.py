# -*- coding: utf-8 -*-
"""T2b 单元测试：4 重鉴权装饰器"""
import os
import sys
os.environ['JWT_SECRET_KEY'] = 'x' * 64  # DEV 测试 secret

sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')

import jwt
from datetime import datetime, timedelta
from flask import Flask, g, jsonify, request
from api.decorators import require_auth, require_role, require_owner_or_admin, audit_log, JWT_SECRET

# 创建 Flask app 用于测试
app = Flask(__name__)
app.config['TESTING'] = True

# 测试路由
@app.route('/api/test_no_auth')
@require_auth
def test_no_auth():
    return jsonify({'code': 0, 'message': 'ok'})

@app.route('/api/test_admin')
@require_auth
@require_role('admin', 'manager')
def test_admin():
    return jsonify({'code': 0, 'message': 'admin ok'})

@app.route('/api/test_worker')
@require_auth
@require_role('worker')
def test_worker():
    return jsonify({'code': 0, 'message': 'worker ok'})

# 1. 测试无 token
print('[1/8] 无 token 测试')
client = app.test_client()
r = client.get('/api/test_no_auth')
assert r.status_code == 401, f'应 401，实际 {r.status_code}'
print(f'   PASS: status={r.status_code}')

# 2. 测试有效 token
print('[2/8] 有效 token 测试')
valid_token = jwt.encode(
    {'uid': 'u1', 'role': 'admin', 'exp': datetime.now() + timedelta(hours=1)},
    JWT_SECRET, algorithm='HS256'
)
r = client.get('/api/test_admin', headers={'Authorization': f'Bearer {valid_token}'})
assert r.status_code == 200, f'应 200，实际 {r.status_code} body={r.data}'
print(f'   PASS: status={r.status_code}')

# 3. 测试过期 token
print('[3/8] 过期 token 测试')
expired_token = jwt.encode(
    {'uid': 'u1', 'role': 'admin', 'exp': datetime.utcnow() - timedelta(hours=1)},
    JWT_SECRET, algorithm='HS256'
)
r = client.get('/api/test_admin', headers={'Authorization': f'Bearer {expired_token}'})
assert r.status_code == 401, f'应 401，实际 {r.status_code}'
print(f'   PASS: status={r.status_code}')

# 4. 测试无效 token
print('[4/8] 无效 token 测试')
r = client.get('/api/test_admin', headers={'Authorization': 'Bearer invalid_xxx'})
assert r.status_code == 401, f'应 401，实际 {r.status_code}'
print(f'   PASS: status={r.status_code}')

# 5. 测试角色匹配（admin → admin 路由）
print('[5/8] 角色匹配测试')
admin_token = jwt.encode(
    {'uid': 'u1', 'role': 'admin', 'exp': datetime.utcnow() + timedelta(hours=1)},
    JWT_SECRET, algorithm='HS256'
)
r = client.get('/api/test_admin', headers={'Authorization': f'Bearer {admin_token}'})
assert r.status_code == 200
print(f'   PASS: admin 访问 admin 路由')

# 6. 测试角色不匹配（worker → admin 路由）
print('[6/8] 角色不匹配测试')
worker_token = jwt.encode(
    {'uid': 'u2', 'role': 'worker', 'exp': datetime.now() + timedelta(hours=1)},
    JWT_SECRET, algorithm='HS256'
)
r = client.get('/api/test_admin', headers={'Authorization': f'Bearer {worker_token}'})
assert r.status_code == 403, f'应 403，实际 {r.status_code}'
print(f'   PASS: worker 访问 admin 路由被拒')

# 7. 测试 worker 路由
print('[7/8] worker 路由测试')
r = client.get('/api/test_worker', headers={'Authorization': f'Bearer {worker_token}'})
assert r.status_code == 200
print(f'   PASS: worker 访问 worker 路由')

# 8. 装饰器集成
print('[8/8] 装饰器签名验证')
from api.decorators import require_auth, require_role, require_owner_or_admin, audit_log
assert callable(require_auth)
assert callable(require_role)
assert callable(require_owner_or_admin)
assert callable(audit_log)
print('   PASS: 4 个装饰器全部 callable')

print('\n8/8 全部通过')
