#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""找 4 工单的实际归属表"""
import os
import sys
import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = {"host": "127.0.0.1", "port": 3306, "user": "root", "password": "88888888", "charset": "utf8mb4"}
conn = pymysql.connect(**DB)
cur = conn.cursor()

# 跨库搜 4 工单所在表(用 prepared statement 防止 SQL 注入)
for order in ['ORD-202604210004', 'ORD-202605020001', 'ORD-202604210002', 'ORD-202605010001']:
    print(f"\n=== {order} ===")
    cur.execute("""
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM information_schema.TABLES t
        WHERE TABLE_SCHEMA NOT IN ('mysql','information_schema','performance_schema','sys')
          AND TABLE_TYPE='BASE TABLE'
          AND EXISTS (
            SELECT 1 FROM information_schema.COLUMNS c
            WHERE c.TABLE_SCHEMA = t.TABLE_SCHEMA AND c.TABLE_NAME = t.TABLE_NAME
              AND c.COLUMN_NAME IN ('order_no','workorder_no')
          )
    """)
    for r in cur.fetchall():
        schema, tbl = r
        try:
            cur.execute(f"SELECT COUNT(*) FROM `{schema}`.`{tbl}` WHERE order_no=%s", (order,))
            cnt = cur.fetchone()[0]
            if cnt > 0:
                print(f"  ✅ {schema}.{tbl}: {cnt} 行")
        except Exception as e:
            print(f"  -- {schema}.{tbl}: ERR {e}")
conn.close()
