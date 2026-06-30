#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""DESCRIBE 真实表结构"""
import pymysql

DB = {"host": "127.0.0.1", "port": 3306, "user": "root", "password": "88888888", "charset": "utf8mb4"}
conn = pymysql.connect(database="steel_belt", **DB)
cur = conn.cursor()

TABLES = [
    ("steel_belt", "orders"),
    ("steel_belt", "process_sub_steps"),
    ("steel_belt", "production_orders"),
    ("steel_belt", "process_records"),
    ("steel_belt", "quality_records"),
    ("container_center", "data_packages"),
    ("container_center", "process_names"),
]

for schema, tbl in TABLES:
    try:
        cur.execute(f"SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT "
                    f"FROM information_schema.COLUMNS "
                    f"WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION", (schema, tbl))
        cols = cur.fetchall()
        print(f"\n=== {schema}.{tbl} ({len(cols)} 列) ===")
        for c in cols:
            print(f"  {c[0]:30s} {c[1]:30s} nullable={c[2]} key={c[3]} default={c[4]}")
    except Exception as e:
        print(f"\n!!! {schema}.{tbl} ERROR: {e}")

conn.close()
