#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""V2 验证:用 5002 HTTP API 取 4 工单的 work_order 列表"""
import json, urllib.request
ORDERS = ["ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"]
url = "http://127.0.0.1:5002/api/v4/work_order?page=1&size=2000"
r = urllib.request.urlopen(url, timeout=10)
data = json.loads(r.read().decode("utf-8"))
items = data.get("items", data.get("data", []))
print(f"5002 work_order 总数: {len(items)}")

# 按 order_no 分组
from collections import defaultdict
by_order = defaultdict(list)
for it in items:
    if not isinstance(it, dict): continue
    d = it.get("doc_data", it.get("data", it.get("content", {})))
    if isinstance(d, str):
        try: d = json.loads(d)
        except: d = {}
    ono = (isinstance(d, dict) and (d.get("order_no") or d.get("related_order"))) or it.get("order_no") or it.get("related_order") or "?"
    by_order[ono].append({
        "id": it.get("id", ""),
        "status": it.get("status", ""),
        "doc_type": it.get("doc_type", ""),
        "process": (isinstance(d, dict) and (d.get("process_name") or d.get("related_process"))) or "",
        "title": (it.get("title", "") or "")[:25] or (isinstance(d, dict) and (d.get("title", "") or "")[:25]) or ""
    })

for o in ORDERS:
    items_o = by_order.get(o, [])
    print(f"\n=== {o} ({len(items_o)} 条) ===")
    for it in items_o:
        print(f"  [{it['id'][:14]:14s}] {it['doc_type']:15s} st={it['status']:12s} proc={it['process']!r:15s} title={it['title']!r}")
