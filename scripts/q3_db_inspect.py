#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q3 看 data_packages 表中 4 工单原始数据 + content"""
import json
import os
import sys
import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "88888888"),
    "database": "container_center",
    "charset": "utf8mb4",
}

conn = pymysql.connect(**DB)
cur = conn.cursor()
cur.execute("SET NAMES utf8mb4")

TARGETS = ["ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"]
for order in TARGETS:
    print(f"\n=== {order} (data_packages 原始) ===")
    cur.execute("""
        SELECT id, data_type, status, related_process, target_operator,
               completed_qty, progress_qty, actual_qty, title, content, created_at
        FROM data_packages
        WHERE related_order=%s
        ORDER BY id ASC
    """, (order,))
    rows = cur.fetchall()
    print(f"  总数: {len(rows)}")
    for r in rows:
        rid, dt, st, rp, top, cq, pq, aq, title, content, ca = r
        # 解析 content
        if isinstance(content, str) and content and content[0] in ('{', '['):
            try:
                content_d = json.loads(content)
            except Exception:
                content_d = None
        else:
            content_d = None
        # content 关键字段
        c_summary = ""
        if content_d:
            for k in ('planned_qty', 'process_name', 'operator_id', 'operator_name',
                      'inspection_type', 'material_name', 'spec', 'quantity', 'unit'):
                if k in content_d:
                    c_summary += f" {k}={content_d[k]!r}"
        print(f"  [{rid[:8]}] dt={dt!r:20s} st={st!r:18s} rp={rp!r:20s} cq={cq} pq={pq} aq={aq} op={top or '-':12s} t={title!r}")
        if c_summary:
            print(f"     content:{c_summary}")
