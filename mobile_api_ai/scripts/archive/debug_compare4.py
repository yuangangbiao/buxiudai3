# -*- coding: utf-8 -*-
import json

with open(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center_data.json', 'r', encoding='utf-8') as f:
    dc_data = json.load(f)

processes = dc_data.get('processes', [])
print(f"=== 调度中心 {len(processes)} 个流程详情 ===\n")
for p in processes:
    print(f"order_no: '{p.get('order_no')}'")
    print(f"  id: {p.get('id')}")
    print(f"  status: {p.get('status')}")
    print(f"  flow_type: {p.get('flow_type')}")
    print(f"  current_step: {p.get('current_step')}")
    print(f"  created_at: {p.get('created_at')}")
    print(f"  updated_at: {p.get('updated_at')}")
    print(f"  steps: {p.get('steps')}")
    print(f"  product_name: {p.get('product_name')}")
    print(f"  quantity: {p.get('quantity')}")
    print()

# Check dispatch_log to see how these were created
print("\n=== 调度日志中与这4个工单相关的记录 ===")
dispatch_log = dc_data.get('dispatch_log', [])
for log in dispatch_log:
    order_no = log.get('order_no', '')
    if any(p.get('order_no') in order_no or order_no in p.get('order_no', '') for p in processes):
        print(f"  {log.get('timestamp')} | {log.get('type')} | order_no={order_no} | result={log.get('result','')}")

# Check work_orders section
print("\n=== work_orders 节点 ===")
work_orders = dc_data.get('work_orders', [])
print(f"work_orders count: {len(work_orders)}")
for wo in work_orders[:10]:
    print(f"  {wo}")
