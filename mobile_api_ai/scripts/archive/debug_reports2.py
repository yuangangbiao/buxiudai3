# -*- coding: utf-8 -*-
import sqlite3
import json

conn = sqlite3.connect(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db')
cur = conn.cursor()

print("=== V5 report类型 - 全部72条记录  工序(process_name)分析 ===\n")
cur.execute("SELECT id, content FROM data_packages WHERE data_type='report'")
rows = cur.fetchall()

# 分类统计
has_work_order = []  # 有order_no的记录
no_work_order = []    # 无order_no的记录

for row in rows:
    c = json.loads(row[1])
    on = c.get('order_no', '')
    wo = c.get('order_no', '')
    pn = c.get('process_name', '')
    title = c.get('title', '')
    if wo and wo.strip():
        has_work_order.append({'id': row[0], 'order_no': on, 'order_no': wo, 'process_name': pn, 'title': title})
    else:
        no_work_order.append({'id': row[0], 'order_no': on, 'order_no': wo, 'process_name': pn, 'title': title})

print(f"有 order_no 的记录: {len(has_work_order)}条")
for r in has_work_order:
    print(f"  order_no={r['order_no']}, order_no={r['order_no']}, process={r['process_name']}")

print(f"\n无 order_no 的记录: {len(no_work_order)}条")
# 按order_no分组，看工序分布
from collections import defaultdict
by_order = defaultdict(list)
for r in no_work_order:
    by_order[r['order_no']].append(r)

for on, items in sorted(by_order.items()):
    print(f"\n  order_no={on} ({len(items)}条报工):")
    for r in items:
        print(f"    process={r['process_name'] or '(空)'}, title={r['title'] or '(空)'}")

conn.close()
