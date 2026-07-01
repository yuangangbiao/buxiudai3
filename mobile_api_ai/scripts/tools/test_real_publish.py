import sys
sys.stdout = open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\scripts\tools\real_test.txt', 'w', encoding='utf-8', buffering=1)
sys.stderr = sys.stdout

import requests, json

print("=== 测试 POST /api/schedule/publish ===")

# 测试发送
try:
    r = requests.post(
        'http://localhost:5002/api/schedule/publish',
        json={
            'order_no': 'WO-REAL-TEST',
            'order_no': 'ORD-REAL-TEST',
            'product_name': '真实测试产品',
            'quantity': 100,
            'unit': '件',
            'plan_start': '2026-05-21',
            'plan_end': '2026-05-30',
            'customer_name': '真实测试客户',
            'notes': '验证发布链路'
        },
        timeout=10
    )
    data = r.json()
    print(f"POST status: {r.status_code}")
    print(f"POST code: {data.get('code')}")
    print(f"POST message: {data.get('message')}")
    print(f"POST full: {json.dumps(data, ensure_ascii=False)}")
except Exception as e:
    print(f"POST 失败: {e}")

# 检查端口
import socket
for port in [5002, 5003, 5008]:
    sock = socket.socket()
    sock.settimeout(2)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    print(f"端口 {port}: {'监听中' if result == 0 else f'未监听({result})'}")

sys.stdout.close()
sys.stdout = sys.__stdout__
print("Done")
