# -*- coding: utf-8 -*-
import pymysql
import os
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Command timed out")

def load_env():
    for line in open(".env", encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

load_env()

print("=" * 50)
print("修复 production_orders 唯一索引问题")
print("=" * 50)

remote_conn = pymysql.connect(
    host="192.168.0.101",
    port=3306,
    user="root",
    password=os.getenv("MYSQL_PASSWORD", ""),
    database="steel_belt",
    charset="utf8mb4",
    connect_timeout=60,
    read_timeout=60,
    write_timeout=60
)
remote_conn.autocommit(True)
print("连接成功!")

remote_cursor = remote_conn.cursor()

print("\n检查当前索引状态...")
remote_cursor.execute("SHOW INDEX FROM production_orders")
for row in remote_cursor.fetchall():
    if 'order_id' in str(row):
        print(f"  {row}")

print("\n开始修复...")

# Step 1: Check if we can drop the index directly with FK_CHECKS=0
print("[1] 禁用外键检查...")
remote_cursor.execute("SET GLOBAL FOREIGN_KEY_CHECKS=0")
print("  完成")

# Step 2: Try to drop the index
print("[2] 删除唯一索引...")
try:
    remote_cursor.execute("DROP INDEX idx_production_orders_order_id ON production_orders")
    print("  成功删除唯一索引!")
except Exception as e:
    print(f"  错误: {e}")

# Step 3: Create non-unique index
print("[3] 创建普通索引...")
try:
    remote_cursor.execute("CREATE INDEX idx_production_orders_order_id ON production_orders(order_id)")
    print("  成功创建普通索引!")
except Exception as e:
    print(f"  错误: {e}")

# Step 4: Re-enable FK checks
print("[4] 启用外键检查...")
remote_cursor.execute("SET GLOBAL FOREIGN_KEY_CHECKS=1")
print("  完成")

# Step 5: Verify
print("\n验证索引...")
remote_cursor.execute("""
    SELECT INDEX_NAME, NON_UNIQUE
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = 'steel_belt'
    AND TABLE_NAME = 'production_orders'
    AND COLUMN_NAME = 'order_id'
""")
for row in remote_cursor.fetchall():
    print(f"  {row}")

remote_cursor.close()
remote_conn.close()
print("\n完成!")
