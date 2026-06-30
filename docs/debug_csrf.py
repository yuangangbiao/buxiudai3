# -*- coding: utf-8 -*-
"""调试 CSRF 500 问题"""
import requests, json

BASE = 'http://127.0.0.1:5001'

print('1. 无 session 的 POST (期望 403，实际 500?):')
h = {'Content-Type': 'application/json', 'X-CSRF-Token': 'wrong'}
try:
    r = requests.post(f'{BASE}/api/material/add',
                       json={'order_id': 1, 'material_name': 'test'},
                       headers=h, timeout=5)
    print(f'   status={r.status_code} body={r.text[:200]}')
except Exception as e:
    print(f'   error: {e}')

print('\n2. 带 session cookie 的 POST (CSRF 正确):')
s = requests.Session()
r2 = s.post(f'{BASE}/api/login', json={'username': '测试'}, timeout=5)
print(f'   login: {r2.status_code} {r2.json()}')
csrf = r2.json().get('data', {}).get('csrf_token', '')
print(f'   CSRF token: {csrf}')
r3 = s.post(f'{BASE}/api/material/add',
             json={'order_id': 1, 'material_name': 'test'},
             headers={'X-CSRF-Token': csrf}, timeout=5)
print(f'   add_material (正确): status={r3.status_code} body={r3.text[:300]}')
