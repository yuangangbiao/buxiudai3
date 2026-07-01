# -*- coding: utf-8 -*-
import json
import sqlite3

# 1. Read dispatch_center_data.json
with open(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center_data.json', 'r', encoding='utf-8') as f:
    dc_data = json.load(f)

processes = dc_data.get('processes', [])
print(f"=== 调度中心 dispatch_center_data.json ===")
print(f"流程数量: {len(processes)}")
for p in processes:
    print(f"  {p.get('order_no')} | {p.get('status')} | {p.get('flow_type')} | created={p.get('created_at','')[:10]}")

# 2. Read V5 storage (wechat_container.db)
print(f"\n=== 容器中心 V5存储 (wechat_container.db) ===")
conn = sqlite3.connect(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db')
cur = conn.cursor()

cur.execute('SELECT data_type, COUNT(*) FROM data_packages GROUP BY data_type')
type_counts = cur.fetchall()
print(f"数据包类型分布:")
for dtype, count in type_counts:
    print(f"  {dtype}: {count}")

# Get distinct work_order_nos
cur.execute('SELECT DISTINCT content FROM data_packages')
work_orders = set()
for row in cur.fetchall():
    try:
        content = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        if isinstance(content, dict):
            wo = content.get('order_no') or content.get('order_no')
            if wo:
                work_orders.add(wo)
    except Exception as e:
        print(f"[debug_compare] 解析数据包内容失败: {e}")

print(f"\nV5存储中的订单号 (共{len(work_orders)}个):")
for wo in sorted(work_orders):
    print(f"  {wo}")

conn.close()

# 3. Check data_types
print(f"\n=== 数据对比 ===")
dc_order_nos = set(p.get('order_no') for p in processes if p.get('order_no'))
print(f"调度中心订单号: {sorted(dc_order_nos)}")
print(f"V5存储订单号: {sorted(work_orders)}")
print(f"共同订单号: {sorted(dc_order_nos & work_orders)}")
print(f"仅在调度中心: {sorted(dc_order_nos - work_orders)}")
print(f"仅在V5存储: {sorted(work_orders - dc_order_nos)}")
