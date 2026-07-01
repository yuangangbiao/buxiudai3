# -*- coding: utf-8 -*-
import sqlite3
import json

conn = sqlite3.connect(r'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db')
cur = conn.cursor()

print("=== data_packages 表结构 ===")
cur.execute("PRAGMA table_info(data_packages)")
for col in cur.fetchall():
    print(f"  {col[1]}: {col[2]}")

print("\n=== V5 report item 顶层字段 ===")
cur.execute("SELECT id, data_type, title, source, status, created_at FROM data_packages WHERE data_type='report' LIMIT 3")
for row in cur.fetchall():
    print(f"  id={row[0]}, source={row[3]}, status={row[4]}, created_at={row[5]}")

print("\n=== content中的时间字段 ===")
cur.execute("SELECT content FROM data_packages WHERE data_type='report' LIMIT 3")
for row in cur.fetchall():
    c = json.loads(row[0])
    print(f"  keys in content: {list(c.keys())}")

conn.close()
