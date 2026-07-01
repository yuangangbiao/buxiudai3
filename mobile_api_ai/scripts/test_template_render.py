"""测试 dispatch_center 模板渲染"""
import os, sys
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _base)

import os
os.environ['CONTAINER_CENTER_URL'] = 'http://localhost:5002'

from app import create_app
app = create_app()

with app.test_client() as c:
    r = c.get('/api/dispatch-center/')
    print(f'GET /api/dispatch-center/: HTTP {r.status_code}')
    print(f'  响应体长度: {len(r.data)} bytes')
    print(f'  Content-Type: {r.content_type}')

    body = r.data.decode('utf-8')
    keywords = ['调度中心', 'Dispatch Center', 'switchTab', 'dispatch_center.js']
    for kw in keywords:
        found = kw in body
        print(f'  包含 "{kw}": {"OK" if found else "MISSING"}')

print('=== DONE ===')
