# -*- coding: utf-8 -*-
import json
import sqlite3

conn = sqlite3.connect(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db')
cur = conn.cursor()

print("=== order_production 类型 (主软件同步的工单) ===")
cur.execute("SELECT id, related_order, title, status, created_at FROM data_packages WHERE data_type='order_production'")
for row in cur.fetchall():
    print(f"  id={row[0]}, order={row[1]}, title={row[2]}, status={row[3]}, created={row[4]}")

print("\n=== material 类型 ===")
cur.execute("SELECT id, related_order, title, status, created_at FROM data_packages WHERE data_type='material'")
for row in cur.fetchall():
    print(f"  id={row[0]}, order={row[1]}, title={row[2]}, status={row[3]}, created={row[4]}")

print("\n=== quality 类型 ===")
cur.execute("SELECT id, related_order, title, status, created_at FROM data_packages WHERE data_type='quality'")
for row in cur.fetchall():
    print(f"  id={row[0]}, order={row[1]}, title={row[2]}, status={row[3]}, created={row[4]}")

print("\n=== report 类型样本 (前5条) ===")
cur.execute("SELECT id, related_order, title, status, created_at FROM data_packages WHERE data_type='report' LIMIT 5")
for row in cur.fetchall():
    print(f"  id={row[0]}, order={row[1]}, title={row[2]}, status={row[3]}, created={row[4]}")

print("\n=== 调度中心 4个流程的订单号 ===")
with open(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center_data.json', 'r', encoding='utf-8') as f:
    dc_data = json.load(f)
processes = dc_data.get('processes', [])
for p in processes:
    print(f"  order_no={p.get('order_no')}, status={p.get('status')}")

conn.close()
