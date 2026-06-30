#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q2 详细分析 4 个工单的每个卡片原始数据"""
import json
import os

OUT_DIR = r"d:\yuan\不锈钢网带跟单3.0\docs\debug\order_state"
ORDERS = ["ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"]


def dump_card(label, items, all_status=("pending", "created", "distributed", "acknowledged", "in_progress", "completed", "withdrawn")):
    if not items:
        print(f"  [{label}] 0 条")
        return
    print(f"  [{label}] {len(items)} 条:")
    for i, it in enumerate(items[:15]):
        st = it.get("status", "?")
        st_ok = "✅" if st in all_status else f"⚠️ 不在标准 status: {all_status}"
        related = it.get("related_process", "-")
        pq = it.get("planned_qty", "-")
        cq = it.get("completed_qty", "-")
        op = it.get("operator_name") or it.get("target_operator") or "-"
        ca = (it.get("created_at", "") or "")[:19]
        pkg_id = it.get("id", "-")
        title = it.get("title", "")
        print(f"    [{i}] id={pkg_id} {st_ok} st={st:18s} rp={related!r:25s} pq={pq} cq={cq} op={op}  {ca}  t={title!r}")
    if len(items) > 15:
        print(f"    ... ({len(items) - 15} more)")


for order_no in ORDERS:
    print(f"\n{'='*70}\n{order_no}\n{'='*70}")
    src = open(os.path.join(OUT_DIR, f"{order_no}.json"), encoding="utf-8").read()
    data = json.loads(src)
    d = data.get("data") or {}

    # 顶层元数据
    print(f"  order_no={d.get('order_no')}")
    print(f"  status={d.get('status')}  customer={d.get('customer_name')}")
    print(f"  stats={d.get('stats')}")
    print(f"  steps={len(d.get('steps') or [])} 条 (流程模板步骤)")

    # 每个卡片详细
    for card_name in ["process_tasks", "flow_steps", "flow_production",
                      "material_tasks", "quality_tasks", "repair_tasks", "outsource_tasks"]:
        dump_card(card_name, d.get(card_name) or [])
