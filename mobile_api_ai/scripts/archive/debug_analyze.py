# -*- coding: utf-8 -*-
import urllib.request
import json

r = urllib.request.urlopen('http://localhost:5003/api/dispatch-center/processes')
data = json.loads(r.read().decode())
processes = data.get('data', [])

print(f"=== 调度中心 38 个流程 ===\n")
for i, p in enumerate(processes, 1):
    print(f"{i:2d}. order_no={p.get('order_no'):<25} status={p.get('status'):<15} flow={p.get('flow_type'):<20} step={p.get('current_step')} qty={p.get('quantity')} product={p.get('product_name')}")

print(f"\n=== 统计 ===")
order_nos = [p.get('order_no') for p in processes]
from collections import Counter
cnt = Counter(order_nos)
dups = {k: v for k, v in cnt.items() if v > 1}
print(f"总数: {len(processes)}, 唯一订单号: {len(set(order_nos))}")
if dups:
    print(f"重复订单号: {dups}")
else:
    print("无重复订单号")

# Check V5 storage for order_production type (主软件同步)
print(f"\n=== V5存储 order_production (主软件同步的工单) ===")
import sqlite3
conn = sqlite3.connect(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db')
cur = conn.cursor()
cur.execute("SELECT id, title, status, related_order FROM data_packages WHERE data_type='order_production'")
for row in cur.fetchall():
    print(f"  id={row[0]}, title={row[1]}, status={row[2]}, related_order={row[3]}")

# Check report type - find the most common order_no values
print(f"\n=== V5 report类型 订单号分布 (报工数据) ===")
cur.execute("SELECT content FROM data_packages WHERE data_type='report' LIMIT 3")
for row in cur.fetchall():
    c = json.loads(row[0])
    print(f"  order_no={c.get('order_no')}, order_no={c.get('order_no')}")

conn.close()
