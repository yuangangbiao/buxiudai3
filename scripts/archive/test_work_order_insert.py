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

# Test INSERT into production_orders
print("Testing INSERT into production_orders...")

# First check if there's an order we can use
remote_cursor.execute("SELECT id, order_no FROM orders WHERE is_deleted=0 LIMIT 1")
order = remote_cursor.fetchone()
if order:
    print(f"Using order ID: {order[0]}, order_no: {order[1]}")

    # Try to insert a production_order
    try:
        remote_cursor.execute("""
            INSERT INTO production_orders (
                work_order_no, order_id, priority, status
            ) VALUES (%s, %s, %s, %s)
        """, ("WO-TEST-001", order[0], 5, "pending"))
        remote_conn.commit()
        print("INSERT SUCCESS! New ID:", remote_cursor.lastrowid)

        # Clean up test data
        remote_cursor.execute("DELETE FROM production_orders WHERE work_order_no='WO-TEST-001'")
        remote_conn.commit()
        print("Test record deleted.")
    except Exception as e:
        print(f"INSERT FAILED: {e}")
else:
    print("No valid orders found!")

# Check for process_calc_rules
print()
print("Checking process_calc_rules...")
remote_cursor.execute("SELECT COUNT(*) FROM process_calc_rules")
count = remote_cursor.fetchone()[0]
print(f"process_calc_rules count: {count}")

# Check for process_rules
print()
print("Checking process_rules...")
remote_cursor.execute("SELECT COUNT(*) FROM process_rules")
count = remote_cursor.fetchone()[0]
print(f"process_rules count: {count}")

# Check for process_templates
print()
print("Checking process_templates...")
remote_cursor.execute("SELECT COUNT(*) FROM process_templates")
count = remote_cursor.fetchone()[0]
print(f"process_templates count: {count}")

remote_cursor.close()
remote_conn.close()
