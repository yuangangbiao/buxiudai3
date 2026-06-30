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

# Check orders structure
remote_cursor.execute("SHOW COLUMNS FROM orders")
cols = [row[0] for row in remote_cursor.fetchall()]
print("Orders table columns (%d):" % len(cols))
for c in cols:
    print(" ", c)

# Check if mesh_size exists
print()
if "mesh_size" in cols:
    print("mesh_size column EXISTS")
else:
    print("mesh_size column MISSING")

# Check orders data
print()
remote_cursor.execute("SELECT COUNT(*) FROM orders WHERE is_deleted=0")
count = remote_cursor.fetchone()[0]
print("Valid orders: %d" % count)

remote_cursor.close()
remote_conn.close()
