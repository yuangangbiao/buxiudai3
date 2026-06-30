# -*- coding: utf-8 -*-
import pymysql
import os
import sys

def load_env():
    for line in open(".env", encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

load_env()

print("Connecting to remote database...")
remote_conn = pymysql.connect(
    host="192.168.0.101",
    port=3306,
    user="root",
    password=os.getenv("MYSQL_PASSWORD", ""),
    database="steel_belt",
    charset="utf8mb4",
    connect_timeout=10
)
print("Connected!")

remote_cursor = remote_conn.cursor()

# Disable foreign key checks temporarily
print("Disabling foreign key checks...")
remote_cursor.execute("SET FOREIGN_KEY_CHECKS=0")
remote_conn.commit()

print("Dropping index...")
remote_cursor.execute("DROP INDEX idx_production_orders_order_id ON production_orders")
remote_conn.commit()
print("Index dropped!")

print("Creating new index...")
remote_cursor.execute("CREATE INDEX idx_production_orders_order_id ON production_orders(order_id)")
remote_conn.commit()
print("Index created!")

print("Re-enabling foreign key checks...")
remote_cursor.execute("SET FOREIGN_KEY_CHECKS=1")
remote_conn.commit()

print("Verifying...")
remote_cursor.execute("""
    SELECT INDEX_NAME, NON_UNIQUE
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = 'steel_belt'
    AND TABLE_NAME = 'production_orders'
    AND INDEX_NAME = 'idx_production_orders_order_id'
""")
result = remote_cursor.fetchone()
if result:
    print(f"Index: {result[0]}, NON_UNIQUE: {result[1]}")
    if result[1] == 1:
        print("SUCCESS! Index is now non-unique.")
    else:
        print("FAILED! Index is still unique.")

remote_cursor.close()
remote_conn.close()
print("Done!")
