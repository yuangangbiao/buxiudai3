#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q-FINAL 查 4 工单主表数据(orders + process_sub_steps)"""
import os
import sys
import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = {"host": "127.0.0.1", "port": 3306, "user": "root", "password": "88888888", "charset": "utf8mb4"}
conn = pymysql.connect(database="steel_belt", **DB)
cur = conn.cursor()
cur.execute("SET NAMES utf8mb4")

ORDERS = ["ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"]

print("=== orders 4 工单主数据 ===")
cur.execute("""
    SELECT order_no, status, product_name, customer_name, quantity, completed_qty, qualified_qty,
           started_at, completed_at, migrated_from
    FROM orders
    WHERE order_no IN (%s, %s, %s, %s)
""", ORDERS)
for r in cur.fetchall():
    print(f"\n  {r[0]}:")
    for k, v in zip(("order_no", "status", "product_name", "customer_name", "quantity",
                     "completed_qty", "qualified_qty", "started_at", "completed_at", "migrated_from"), r):
        print(f"    {k} = {v!r}")

print("\n\n=== process_sub_steps 4 工单统计(真正的工序报工主表) ===")
for o in ORDERS:
    cur.execute("""
        SELECT step_name, COUNT(*) AS batches, SUM(quantity) AS total_qty,
               SUM(qualified_qty) AS total_qualified, operator
        FROM process_sub_steps
        WHERE order_no=%s AND is_deleted=0
        GROUP BY step_name, operator
        ORDER BY step_name
    """, (o,))
    rows = cur.fetchall()
    print(f"\n  {o} ({len(rows)} step/operator 组合):")
    for r in rows:
        print(f"    {r[0]:18s} batches={r[1]} qty={r[2]} qualified={r[3]} op={r[4]!r}")

print("\n\n=== quality_records 4 工单统计 ===")
for o in ORDERS:
    cur.execute("SELECT COUNT(*), SUM(quantity), SUM(qualified_qty) FROM quality_records WHERE order_no=%s AND is_deleted=0", (o,))
    print(f"  {o}: count={cur.fetchone()}")

conn.close()
