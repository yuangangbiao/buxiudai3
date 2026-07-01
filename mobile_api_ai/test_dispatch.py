# -*- coding: utf-8 -*-
import requests
import json

url = "http://localhost:5002/api/dispatch"
payload = {
    "operator_id": "OP001",
    "order_no": "TEST-001",
    "order_no": "WO-TEST-001",
    "process": "测试工序",
    "quantity": 100,
    "priority": "normal",
    "source": "test"
}

print(f"发送请求到: {url}")
print(f"Payload: {json.dumps(payload, ensure_ascii=False)}")

try:
    r = requests.post(url, json=payload, timeout=30)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")
