#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pymysql
DB = {"host": "127.0.0.1", "port": 3306, "user": "root", "password": "88888888", "charset": "utf8mb4"}
conn = pymysql.connect(database="container_center", **DB)
cur = conn.cursor()

print("=== container_center 全部表 ===")
cur.execute("SHOW TABLES")
for (t,) in cur.fetchall():
    print(f"  {t[0]}")

print("\n=== tbl_documents 总数 ===")
cur.execute("SELECT doc_type, COUNT(*) FROM tbl_documents GROUP BY doc_type")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]}")

print("\n=== tbl_documents 中 4 工单数据 ===")
cur.execute("""SELECT id, doc_type, status, SUBSTRING(doc_data, 1, 200) as data_preview
               FROM tbl_documents
               WHERE doc_data LIKE '%ORD-202604210004%'
                  OR doc_data LIKE '%ORD-202605020001%'
                  OR doc_data LIKE '%ORD-202604210002%'
                  OR doc_data LIKE '%ORD-202605010001%'""")
rows = cur.fetchall()
print(f"  4 工单相关: {len(rows)} 条")
for r in rows[:20]:
    print(f"    id={r[0]:20s} type={r[1]:15s} st={r[2]:12s} data={r[3][:150]!r}")
conn.close()
