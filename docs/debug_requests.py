# -*- coding: utf-8 -*-
"""调试 requests 导入"""
import requests as req
print(f"requests module: {req.__file__}")
print(f"requests.__version__: {req.__version__}")

BASE = 'http://127.0.0.1:5001'
r = req.post(f'{BASE}/api/login', json={'username': '测试'}, timeout=5)
print(f"type(r): {type(r)}")
print(f"r.json(): {r.json()}")
print(f"r.status_code: {r.status_code}")
