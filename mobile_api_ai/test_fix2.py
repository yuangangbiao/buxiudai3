# -*- coding: utf-8 -*-
import urllib.request
import json

url = "http://localhost:5003/api/dispatch-center/processes"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

processes = data.get('data', [])
print(f"=== 调度中心当前流程 ({len(processes)}条) ===")
for p in processes:
    print(f"  {p.get('order_no')} | {p.get('status')} | product={p.get('product_name')} | qty={p.get('quantity')}")
