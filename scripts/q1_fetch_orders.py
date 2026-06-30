#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q1 取 4 个工单的 workorder_detail API 原始数据"""
import json
import os
import sys
import urllib.request

ORDERS = [
    "ORD-202604210004",
    "ORD-202605020001",
    "ORD-202604210002",
    "ORD-202605010001",
]

OUT_DIR = r"d:\yuan\不锈钢网带跟单3.0\docs\debug\order_state"
os.makedirs(OUT_DIR, exist_ok=True)

for order_no in ORDERS:
    url = f"http://127.0.0.1:5003/api/dispatch-center/workorder/{order_no}"
    print(f"\n=== {order_no} ===")
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  ERR: {e}")
        continue

    d = data.get("data") or {}
    # 保存原始
    out_path = os.path.join(OUT_DIR, f"{order_no}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  saved -> {out_path}")

    # 摘要
    print(f"  process_tasks   = {len(d.get('process_tasks') or [])}")
    print(f"  flow_steps      = {len(d.get('flow_steps') or [])}")
    print(f"  flow_production = {len(d.get('flow_production') or [])}")
    print(f"  material_tasks  = {len(d.get('material_tasks') or [])}")
    print(f"  quality_tasks   = {len(d.get('quality_tasks') or [])}")
    print(f"  repair_tasks    = {len(d.get('repair_tasks') or [])}")
    print(f"  outsource_tasks = {len(d.get('outsource_tasks') or [])}")
    print(f"  stats = {d.get('stats')}")

    # 每个卡片的 status 分布
    for card_name, items in [
        ("process_tasks",   d.get("process_tasks") or []),
        ("flow_steps",      d.get("flow_steps") or []),
        ("flow_production", d.get("flow_production") or []),
        ("material_tasks",  d.get("material_tasks") or []),
        ("quality_tasks",   d.get("quality_tasks") or []),
        ("repair_tasks",    d.get("repair_tasks") or []),
        ("outsource_tasks", d.get("outsource_tasks") or []),
    ]:
        if not items:
            continue
        status_cnt = {}
        for it in items:
            s = it.get("status", "?")
            status_cnt[s] = status_cnt.get(s, 0) + 1
        print(f"  {card_name:18s} status 分布: {status_cnt}")
