# -*- coding: utf-8 -*-
import json
import sqlite3

conn = sqlite3.connect(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db')
cur = conn.cursor()

# Get raw item structure from V5 storage
cur.execute("SELECT id, data_type, content FROM data_packages LIMIT 2")
rows = cur.fetchall()
print("=== V5存储原始数据结构 (report类型) ===")
for row in rows:
    print(f"\nRow: id={row[0]}, data_type={row[1]}")
    try:
        content = json.loads(row[2]) if isinstance(row[2], str) else row[2]
        print(f"  content keys: {list(content.keys())}")
        print(f"  content.order_no: {content.get('order_no', 'N/A')}")
        print(f"  content.order_no: {content.get('order_no', 'N/A')}")
    except Exception as e:
        print(f"  content (raw): {row[2][:100]} (JSON解析失败: {e})")

# Check how dispatch_center.py interprets it
print("\n\n=== _get_doc_data 模拟 ===")
print("_get_doc_data looks for item.get('doc_data', item.get('data', {}))")
print("V5 item['content'] is NOT 'doc_data' or 'data', so _get_doc_data returns {}!")
print("But 'order_no' is in item['content'], not at item level")
print()

# So the right extraction should be:
print("=== 正确的提取方式 ===")
print("item.get('content', {}).get('order_no') => gets the order_no")

# Check all data_types and their order_no presence
print("\n=== 各类型数据中 order_no 存在情况 ===")
for dtype in ['report', 'order_production', 'quality', 'material']:
    cur.execute(f"SELECT COUNT(*) FROM data_packages WHERE data_type=?", (dtype,))
    total = cur.fetchone()[0]
    cur.execute(f"SELECT content FROM data_packages WHERE data_type=? LIMIT 3", (dtype,))
    sample = cur.fetchall()
    has_order_no = 0
    for row in sample:
        try:
            content = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            if content.get('order_no'):
                has_order_no += 1
        except Exception as e:
            print(f"[debug_compare5] 解析数据包内容失败: {e}")
    print(f"  {dtype}: total={total}, sample_order_no_present={has_order_no}/3")

conn.close()
