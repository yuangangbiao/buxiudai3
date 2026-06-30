#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q3 看 doc_data 实际结构"""
import json
import os
import sys
import urllib.request

# 用 list_processes API 拿原始 data,看 doc_data 怎么来的
url = "http://127.0.0.1:5003/api/dispatch-center/processes?page=1&size=20"
data = json.loads(urllib.request.urlopen(url, timeout=10).read().decode("utf-8"))
processes = data.get("data", [])

# 找 4 个工单的所有 items
TARGETS = {"ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"}
for proc in processes:
    order = proc.get("order_no")
    if order not in TARGETS:
        continue
    print(f"\n=== {order} ===")
    # 看几个字段
    for k in ["status", "product_name", "quantity", "flow_type", "current_step", "process_id"]:
        print(f"  proc.{k} = {proc.get(k)!r}")
    # items 可能是 proc['process_tasks'] 等
    print(f"  keys = {list(proc.keys())}")
