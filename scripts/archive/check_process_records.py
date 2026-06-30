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

# Check process_records structure
remote_cursor.execute("SHOW COLUMNS FROM process_records")
cols = [row[0] for row in remote_cursor.fetchall()]
print("process_records columns (%d):" % len(cols))
for c in cols:
    print(" ", c)

print()
remote_cursor.execute("SELECT COUNT(*) FROM process_records")
count = remote_cursor.fetchone()[0]
print("process_records count: %d" % count)

remote_cursor.execute("SELECT COUNT(*) FROM production_orders")
count = remote_cursor.fetchone()[0]
print("production_orders count: %d" % count)

remote_cursor.close()
remote_conn.close()
