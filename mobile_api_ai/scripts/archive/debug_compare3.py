# -*- coding: utf-8 -*-
import json
import sqlite3

conn = sqlite3.connect(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db')
cur = conn.cursor()

cur.execute("SELECT id, data_type, title, status, created_at FROM data_packages WHERE data_type='order_production'")
print("=== order_production 工单内容 ===")
for row in cur.fetchall():
    print(f"\nid={row[0]}")
    print(f"  type={row[1]}, title={row[2]}, status={row[3]}")
    cur2 = conn.cursor()
    cur2.execute("SELECT content FROM data_packages WHERE id=?", (row[0],))
    content_row = cur2.fetchone()
    if content_row:
        try:
            content = json.loads(content_row[0]) if isinstance(content_row[0], str) else content_row[0]
            print(f"  content: {json.dumps(content, ensure_ascii=False, indent=4)}")
        except Exception as e:
            print(f"  content: {content_row[0]} (JSON解析失败: {e})")
    cur2.close()

conn.close()

# Check what _get_doc_data would extract
print("\n\n=== 分析 _get_doc_data 从 V5 包中提取 order_no ===")
print("V5存储的report类型数据中，大部分是桌面端报工测试数据:")
print("  - source='desktop' (桌面端报工应用)")
print("  - data_type='report'")
print("  - 这些数据没有'order_no'或'order_no'字段")
print()
print("主软件同步的order_production类型:")
print("  - TEST-AUTO-001: 没有related_order，title='订单排产：TEST-AUTO-001'")
print("  - 因此提取不到order_no，backfill无法创建流程")
