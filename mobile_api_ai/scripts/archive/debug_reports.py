# -*- coding: utf-8 -*-
import sqlite3
import json

conn = sqlite3.connect(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db')
cur = conn.cursor()

# Get all report types with their order_no grouping
print("=== V5 report类型 - 按order_no分组统计 ===\n")
cur.execute("SELECT content FROM data_packages WHERE data_type='report'")
rows = cur.fetchall()

from collections import defaultdict
by_order = defaultdict(list)
for row in rows:
    c = json.loads(row[0])
    on = c.get('order_no', 'N/A')
    by_order[on].append(c)

for on, items in sorted(by_order.items()):
    titles = [c.get('title', '') for c in items]
    statuses = [c.get('status', '') for c in items]
    process_names = [c.get('process_name', '') for c in items]
    print(f"order_no: {on}  ({len(items)}条报工记录)")
    for i, (c, title, status, pn) in enumerate(zip(items, titles, statuses, process_names)):
        wo = c.get('order_no', '')
        completed = c.get('completed_qty', 0)
        qualified = c.get('qualified_qty', 0)
        operator = c.get('operator_name', '')
        print(f"  [{i+1}] title={title}, process={pn}, wo={wo}, completed={completed}, qualified={qualified}, operator={operator}")
    print()

conn.close()
