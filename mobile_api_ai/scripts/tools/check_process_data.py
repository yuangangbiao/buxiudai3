import json
fp = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center_data.json'
with open(fp, 'r', encoding='utf-8') as f:
    data = json.load(f)
procs = data.get('processes', [])
print('数据文件中的流程数:', len(procs))
for p in procs[:5]:
    print('  -', p.get('order_no','?'), '|', p.get('product_name','?'), '| flow_type=', p.get('flow_type'), '| status=', p.get('status'))
print()
print('全部keys:', list(data.keys()))
print('rules:', json.dumps(data.get('rules',{}), ensure_ascii=False)[:200])
print('templates count:', len(data.get('templates',[])))
print('messages count:', len(data.get('messages',[])))
