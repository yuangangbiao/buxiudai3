# -*- coding: utf-8 -*-
import urllib.request
import json

url = "http://localhost:5003/api/dispatch-center/debug/cc-workorders"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

print(f"code: {data['code']}")
print(f"total: {data['total']}")
print(f"\n前3条sample的order_no:")
for item in data.get('sample', [])[:3]:
    content = item.get('content', {})
    print(f"  data_type={item['data_type']}, order_no={content.get('order_no', 'N/A')}, title={item.get('title', 'N/A')}")

# Check order_no distribution
print(f"\n=== backfill能匹配到的工单 ===")
all_order_nos = set()
for item in data.get('sample', []):
    content = item.get('content', {})
    on = content.get('order_no', item.get('order_no', ''))
    if on:
        all_order_nos.add(on)

print(f"V5存储中的order_no: {sorted(all_order_nos)[:10]}")
print(f"\n调度中心的4个订单: ['WO-202605004', 'WO-TEST-END-001', 'WO-202605005', 'TEST-001']")
print(f"交集: {sorted(all_order_nos & {'WO-202605004', 'WO-TEST-END-001', 'WO-202605005', 'TEST-001'})}")
