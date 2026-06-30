#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Q-FINAL 4 工单真实数据全探查(用 SELECT * 避免列名错误)"""
import pymysql
import json

DB = {"host": "127.0.0.1", "port": 3306, "user": "root", "password": "88888888", "charset": "utf8mb4"}
ORDERS = ["ORD-202604210004", "ORD-202605020001", "ORD-202604210002", "ORD-202605010001"]

def show_table_cols(database, table):
    conn = pymysql.connect(database=database, **DB)
    cur = conn.cursor()
    cur.execute(f"DESCRIBE {table}")
    print(f"\n--- {database}.{table} 列 ---")
    for r in cur.fetchall():
        print(f"  {r[0]:30s} {r[1]:30s} null={r[2]} key={r[3]} default={r[4]}")
    conn.close()

# 1. orders 列
show_table_cols("steel_belt", "orders")
show_table_cols("steel_belt", "production_orders")

# 2. orders 4 工单
print("\n" + "=" * 80)
print("【1】 steel_belt.orders (SELECT *)")
print("=" * 80)
conn = pymysql.connect(database="steel_belt", **DB)
cur = conn.cursor()
cur.execute("SELECT * FROM orders WHERE order_no IN (%s,%s,%s,%s)", ORDERS)
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    print(f"\n  --- {r[cols.index('order_no')]} ---")
    for c, v in zip(cols, r):
        if v is not None and str(v) != "":
            print(f"    {c:30s} = {v!r}")
conn.close()

# 3. process_records
print("\n" + "=" * 80)
print("【2】 steel_belt.process_records 4 工单")
print("=" * 80)
conn = pymysql.connect(database="steel_belt", **DB)
cur = conn.cursor()
for o in ORDERS:
    cur.execute("""SELECT id, process_name, process_code, display_seq, process_seq,
                          planned_qty, completed_qty, qualified_qty, status, worker, operator,
                          is_outsource, machine_no, batch_no
                   FROM process_records WHERE order_no=%s AND is_deleted=0
                   ORDER BY display_seq, process_seq, id""", (o,))
    rows = cur.fetchall()
    print(f"\n  {o} ({len(rows)} 条):")
    for r in rows:
        print(f"    id={r[0]:>3} seq={r[3]}/{r[4]:<3} {r[2]:5s} {r[1]:18s} plan={r[5] or 0:>5} done={r[6] or 0:>5} qual={r[7] or 0:>5} "
              f"status={r[8]:8s} op={r[9] or r[10]!r:12s} outsrc={r[11]} mc={r[12]!r} batch={r[13]!r}")
conn.close()

# 4. process_sub_steps
print("\n" + "=" * 80)
print("【3】 steel_belt.process_sub_steps 4 工单 (batch 报工)")
print("=" * 80)
conn = pymysql.connect(database="steel_belt", **DB)
cur = conn.cursor()
for o in ORDERS:
    cur.execute("""SELECT id, step_name, batch_no, quantity, qualified_qty, operator,
                          record_date, source, synced
                   FROM process_sub_steps WHERE order_no=%s AND is_deleted=0
                   ORDER BY record_date, id""", (o,))
    rows = cur.fetchall()
    print(f"\n  {o} ({len(rows)} 条 batch):")
    step_summary = {}
    for r in rows:
        sn = r[1]
        step_summary.setdefault(sn, {"count": 0, "qty": 0, "qual": 0})
        step_summary[sn]["count"] += 1
        step_summary[sn]["qty"] += float(r[3] or 0)
        step_summary[sn]["qual"] += float(r[4] or 0)
        print(f"    id={r[0]:>3} {r[1]:18s} batch={r[2][:18]!r:20s} qty={r[3]:>6} qual={r[4]:>6} op={r[5]!r:12s} date={r[6]} src={r[7]} sync={r[8]}")
    print(f"    [按 step 汇总] {len(step_summary)} 工序:")
    for sn, s in step_summary.items():
        print(f"      {sn:18s}: {s['count']:>3} 批, 累计 qty={s['qty']:.1f}, qual={s['qual']:.1f}")
conn.close()

# 5. data_packages
print("\n" + "=" * 80)
print("【4】 container_center.data_packages 4 工单")
print("=" * 80)
conn = pymysql.connect(database="container_center", **DB)
cur = conn.cursor()
for o in ORDERS:
    cur.execute("""SELECT id, data_type, status, target_operator, completed_at,
                          completed_qty, progress_qty, related_process, title
                   FROM data_packages WHERE order_no=%s ORDER BY data_type, id""", (o,))
    rows = cur.fetchall()
    print(f"\n  {o} ({len(rows)} 条):")
    type_count = {}
    status_count = {}
    for r in rows:
        type_count[r[1]] = type_count.get(r[1], 0) + 1
        status_count[r[2]] = status_count.get(r[2], 0) + 1
        print(f"    [{r[1][:25]:25s}] status={r[2][:10]:10s} op={r[3]!r:12s} "
              f"completed_qty={r[5]} progress={r[6]} rel={r[7]!r:15s} title={r[8][:25]!r}")
    print(f"    [data_type 分布] {type_count}")
    print(f"    [status 分布]    {status_count}")
conn.close()

# 6. quality_records
print("\n" + "=" * 80)
print("【5】 steel_belt.quality_records 4 工单")
print("=" * 80)
conn = pymysql.connect(database="steel_belt", **DB)
cur = conn.cursor()
for o in ORDERS:
    cur.execute("""SELECT id, inspection_type, process_name, result, status, review_status,
                          inspector, defect_qty, inspection_no
                   FROM quality_records WHERE order_no=%s ORDER BY id""", (o,))
    rows = cur.fetchall()
    print(f"\n  {o} ({len(rows)} 条):")
    for r in rows:
        print(f"    id={r[0]:>3} type={r[1] or '-':8s} proc={r[2]!r:18s} result={r[3]:6s} status={r[4] or '-':10s} "
              f"review={r[5] or '-':10s} ins={r[6]!r:12s} def={r[7] or 0} no={r[8]!r}")
conn.close()
