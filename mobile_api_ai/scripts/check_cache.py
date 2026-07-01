import json, sys

sys.stdout.reconfigure(encoding='utf-8')

with open('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

processes = data.get('processes', [])
print(f'缓存processes总数: {len(processes)}')

# 只保留生产工单相关的order_no
keep_orders = ['WO-202605005', 'WO-202605006', 'ORD-202604210003', 'ORD-202604290001', '202605006']

for i, p in enumerate(processes):
    order_no = p.get('order_no', '?')
    wo = p.get('order_no', '?')
    is_keep = any(k in order_no or k in wo for k in keep_orders)
    tag = ' [保留]' if is_keep else ' [删除]'
    print(f'  [{i}]{tag} order_no={order_no}, wo={wo}, status={p.get("status","?")}, flow={p.get("flow_type","?")}')
