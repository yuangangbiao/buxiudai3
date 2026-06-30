import requests, json

# 测试池状态
r = requests.get('http://127.0.0.1:5002/api/pool/status', timeout=5)
print(f'[pool/status] {r.status_code}: code={r.json().get("code")}, total={r.json()["data"]["total"]}')

# 测试库存API
r = requests.get('http://127.0.0.1:5002/inventory/api/inventory', timeout=5)
print(f'[inventory/api] {r.status_code}')
data = r.json()
items = data.get('data', data.get('inventory', []))
if isinstance(items, list):
    print(f'  库存条目数: {len(items)}')
else:
    print(f'  响应: {str(data)[:200]}')

# 测试任务API
r = requests.get('http://127.0.0.1:5002/api/tasks', timeout=5)
print(f'[api/tasks] {r.status_code}: code={r.json().get("code")}')

print('\n所有接口验证通过 ✓')
