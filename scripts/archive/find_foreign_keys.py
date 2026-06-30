# -*- coding: utf-8 -*-
import pymysql
import os

def load_env():
    for line in open(".env", encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

load_env()

remote_conn = pymysql.connect(host="192.168.0.101", port=3306, user="root", password=os.getenv("MYSQL_PASSWORD", ""), database="steel_belt", charset="utf8mb4")
remote_cursor = remote_conn.cursor()

# Find foreign keys referencing production_orders
print("Foreign keys referencing production_orders:")
remote_cursor.execute("""
    SELECT
        TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = 'steel_belt'
    AND REFERENCED_TABLE_NAME = 'production_orders'
""")
for row in remote_cursor.fetchall():
    print(f"  {row}")

print()

# Check process_records foreign key
print("Foreign keys in process_records:")
remote_cursor.execute("""
    SELECT
        TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = 'steel_belt'
    AND TABLE_NAME = 'process_records'
    AND REFERENCED_TABLE_NAME IS NOT NULL
""")
for row in remote_cursor.fetchall():
    print(f"  {row}")

remote_cursor.close()
remote_conn.close()
