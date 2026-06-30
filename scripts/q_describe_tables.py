#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查 process_names 和 workorders 表结构"""
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

for table in ("process_names", "workorders"):
    print(f"\n=== {table} ===")
    cur.execute(f"DESCRIBE {table}")
    for r in cur.fetchall():
        print(f"  {r}")

# 物理工序实际数据
# [F16 T16.7 修复] process_names 表已 F6 P9 2026-06-10 DROP (跨库历史表清理, 详见 MEMORY.md L20)
#     原代码: SELECT * FROM process_names LIMIT 5
#     修复: 改用 dispatch_cache.process_departments 内存数据
print("\n=== process_names 实际数据(前 5) ===")
print("[F16 T16.7] process_names 表已 F6 P9 DROP, 改用 dispatch_cache.process_departments")
try:
    from core.config import PROCESS_CODES, _custom_process_codes
    merged = {**PROCESS_CODES, **_custom_process_codes}
    for i, (name, code) in enumerate(merged.items()):
        if i >= 5:
            break
        print(f"  ({name}, {code})")
except Exception as e:
    print(f"  [F6 P9 兼容] 读 dispatch_cache 失败: {e}")

# workorders 4 工单的 status
print("\n=== workorders 4 工单 status ===")
cur.execute("""
    SELECT order_no, status, quantity FROM workorders
    WHERE order_no IN ('ORD-202604210004','ORD-202605020001','ORD-202604210002','ORD-202605010001')
""")
for r in cur.fetchall():
    print(f"  {r}")
conn.close()
