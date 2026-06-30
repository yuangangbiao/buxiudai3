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

conn = pymysql.connect(
    host="192.168.0.101",
    port=3306,
    user="root",
    password=os.getenv("MYSQL_PASSWORD", ""),
    database="steel_belt",
    charset="utf8mb4"
)
cursor = conn.cursor()

cursor.execute("SHOW TABLES")
tables = sorted([list(row)[0] for row in cursor.fetchall()])
print("Remote DB tables (%d):" % len(tables))
for t in tables:
    print(" ", t)

prod_tables = [t for t in tables if "production" in t.lower() or "work_order" in t.lower() or "process" in t.lower()]
print()
print("Production-related tables:")
for t in prod_tables:
    print(" ", t)
