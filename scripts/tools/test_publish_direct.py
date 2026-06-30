# -*- coding: utf-8 -*-
"""直接用代码中的_url + headers方式测试"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import requests, json

# 1) 复制 _actually_send 的逻辑
url = "http://127.0.0.1:5002/api/schedule/publish"
headers = {'Content-Type': 'application/json'}
api_key = os.getenv('CONTAINER_API_KEY', '')
if api_key:
    headers['X-API-Key'] = api_key

payload = {
    'work_order_no': 'WO-DIRECT-001',
    'prod_id': 999,
    'plan_start': '',
    'plan_end': '',
    'order_no': 'ORD-DIRECT-001',
    'customer_group': '测试',
    'product_type': '不锈钢网',
    'material': '304',
    'source': 'main_software',
}

print(f"POST {url}")
print(f"headers={headers}")
print(f"payload={json.dumps(payload, ensure_ascii=False, default=str)[:200]}...")

try:
    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    print(f"\nHTTP {resp.status_code}")
    print(f"Response: {resp.json()}")
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
