import json

cache_file = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center_data.json'

with open(cache_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print('=== 清理前 ===')
for p in data.get('processes', []):
    print(f'  order_no={p.get("order_no","")}, wo={p.get("order_no","")}, quantity={p.get("quantity","")}, product={p.get("product_name","")}, status={p.get("status","")}')

# 记录数
before = len(data.get('processes', []))
print(f'  总数: {before}')

# 清空 processes
data['processes'] = []

with open(cache_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'\n✅ 缓存processes已清空: {before} -> 0 条')
print('请重启调度中心')
