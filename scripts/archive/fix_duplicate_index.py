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

print("Step 1: Drop foreign key constraints that use the unique index...")

# Drop foreign keys
fk_to_drop = [
    ("process_records", "process_records_ibfk_2"),
    ("production_stats", "production_stats_ibfk_2"),
    ("quality_records", "quality_records_ibfk_2"),
]

for table, fk in fk_to_drop:
    try:
        remote_cursor.execute(f"ALTER TABLE {table} DROP FOREIGN KEY {fk}")
        remote_conn.commit()
        print(f"  Dropped: {table}.{fk}")
    except Exception as e:
        print(f"  Error dropping {table}.{fk}: {e}")

print()
print("Step 2: Drop the unique index on order_id...")
try:
    remote_cursor.execute("DROP INDEX idx_production_orders_order_id ON production_orders")
    remote_conn.commit()
    print("  Dropped unique index")
except Exception as e:
    print(f"  Error: {e}")

print()
print("Step 3: Create non-unique index on order_id...")
try:
    remote_cursor.execute("CREATE INDEX idx_production_orders_order_id ON production_orders(order_id)")
    remote_conn.commit()
    print("  Created non-unique index")
except Exception as e:
    print(f"  Error: {e}")

print()
print("Step 4: Recreate foreign keys...")
fk_to_create = [
    ("process_records", "ALTER TABLE process_records ADD CONSTRAINT process_records_ibfk_2 FOREIGN KEY (production_id) REFERENCES production_orders(id)"),
    ("production_stats", "ALTER TABLE production_stats ADD CONSTRAINT production_stats_ibfk_2 FOREIGN KEY (production_id) REFERENCES production_orders(id)"),
    ("quality_records", "ALTER TABLE quality_records ADD CONSTRAINT quality_records_ibfk_2 FOREIGN KEY (production_id) REFERENCES production_orders(id)"),
]

for table, sql in fk_to_create:
    try:
        remote_cursor.execute(sql)
        remote_conn.commit()
        print(f"  Created: {table} foreign key")
    except Exception as e:
        print(f"  Error creating {table} FK: {e}")

print()
print("Step 5: Verify the fix...")
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
        print("FIX SUCCESSFUL! Index is now non-unique.")
    else:
        print("FIX FAILED! Index is still unique.")

remote_cursor.close()
remote_conn.close()
