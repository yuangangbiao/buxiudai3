import urllib.request
import json

print('=== 1. 工单统计 ===')
resp = urllib.request.urlopen('http://127.0.0.1:5003/api/dispatch-center/workorder/stats', timeout=5)
data = json.loads(resp.read())
print(json.dumps(data, ensure_ascii=False, indent=2))

print('\n=== 2. 流程列表 ===')
resp2 = urllib.request.urlopen('http://127.0.0.1:5003/api/dispatch-center/processes', timeout=5)
data2 = json.loads(resp2.read())
items = data2.get('data', [])
print(f'总流程数: {len(items)}')
for p in items:
    print(f"  {p.get('order_no', ''):25s} | {p.get('product_name', ''):15s} | {p.get('status', '')}")

print('\n=== 3. 容器中心健康 ===')
resp3 = urllib.request.urlopen('http://127.0.0.1:5002/health', timeout=5)
print(resp3.read().decode())
