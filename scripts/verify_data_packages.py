#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pymysql
conn = pymysql.connect(database='container_center', host='127.0.0.1', port=3306, user='root', password='88888888', charset='utf8mb4')
cur = conn.cursor()
cur.execute("SELECT id, data_type, order_no, related_order, related_process, status, source FROM data_packages WHERE order_no IN ('ORD-202604210004','ORD-202605020001','ORD-202604210002','ORD-202605010001') ORDER BY order_no, related_process")
rows = cur.fetchall()
print(f'TOTAL: {len(rows)}')
for r in rows:
    print(f'  {r[0][:20]:20s} {r[1]:15s} order_no={r[2]!r:22s} related={r[3]!r:22s} proc={r[4]!r:15s} status={r[5]:12s} src={r[6]}')
conn.close()
