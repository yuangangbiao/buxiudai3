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

# Local
local_conn = pymysql.connect(host="localhost", port=3306, user="root", password=os.getenv("MYSQL_PASSWORD", ""), database="steel_belt", charset="utf8mb4")
local_cursor = local_conn.cursor()

# Remote
remote_conn = pymysql.connect(host="192.168.0.101", port=3306, user="root", password=os.getenv("MYSQL_PASSWORD", ""), database="steel_belt", charset="utf8mb4")
remote_cursor = remote_conn.cursor()

# Check production_orders structure
tables_to_check = ["production_orders", "process_records", "quality_rules", "material_rules"]

for table in tables_to_check:
    print("=" * 50)
    print(f"Table: {table}")
    print("=" * 50)

    local_cursor.execute(f"SHOW CREATE TABLE `{table}`")
    remote_cursor.execute(f"SHOW CREATE TABLE `{table}`")

    local_sql = local_cursor.fetchone()[1]
    remote_sql = remote_cursor.fetchone()[1]

    # Get column info
    local_cursor.execute(f"SHOW COLUMNS FROM `{table}`")
    remote_cursor.execute(f"SHOW COLUMNS FROM `{table}`")

    local_cols = {row[0]: row[1] for row in local_cursor.fetchall()}
    remote_cols = {row[0]: row[1] for row in remote_cursor.fetchall()}

    local_only = set(local_cols.keys()) - set(remote_cols.keys())
    remote_only = set(remote_cols.keys()) - set(local_cols.keys())

    if local_only:
        print(f"LOCAL ONLY: {local_only}")
    if remote_only:
        print(f"REMOTE ONLY: {remote_only}")
    if not local_only and not remote_only:
        print("Columns match")

    print()

local_cursor.close()
local_conn.close()
remote_cursor.close()
remote_conn.close()
