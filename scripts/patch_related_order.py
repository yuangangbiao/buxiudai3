#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P2: 修补 fix_4orders_anomaly.py v2 插入遗漏(related_order + content.order_no)"""
import json
import pymysql
import os
import sys

DB = {"host": "127.0.0.1", "port": 3306, "user": "root", "password": "88888888", "charset": "utf8mb4"}
ORDERS = ["ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"]

conn = pymysql.connect(database="container_center", **DB)
cur = conn.cursor()

# 1. 修补: related_order = order_no
cur.execute("""
    UPDATE data_packages
    SET related_order = order_no
    WHERE order_no IN (%s,%s,%s,%s)
      AND (related_order='' OR related_order IS NULL)
""", ORDERS)
n1 = cur.rowcount
print(f"  [1] 修补 related_order: {n1} 行")

# 2. 修补: content 加上 order_no, process_name
cur.execute("""
    SELECT id, order_no, related_process, content FROM data_packages
    WHERE order_no IN (%s,%s,%s,%s) AND data_type='process_task'
""", ORDERS)
rows = cur.fetchall()
n2 = 0
for rid, ono, proc, content in rows:
    if not content:
        new_content = {"order_no": ono, "process_name": proc or ""}
        cur.execute("UPDATE data_packages SET content=%s WHERE id=%s",
                    (json.dumps(new_content, ensure_ascii=False), rid))
        n2 += 1
    else:
        try:
            d = json.loads(content) if isinstance(content, str) else content
        except Exception:
            d = {}
        d["order_no"] = ono
        d["process_name"] = proc or ""
        cur.execute("UPDATE data_packages SET content=%s WHERE id=%s",
                    (json.dumps(d, ensure_ascii=False), rid))
        n2 += 1
print(f"  [2] 修补 content.order_no/process_name: {n2} 行")

conn.commit()
conn.close()
print("  [✓] 修补完成")
