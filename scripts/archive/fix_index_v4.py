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
    connect_timeout=60
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

# Create a new non-unique index with a different name first
print("[1] 创建新的普通索引...")
try:
    remote_cursor.execute("CREATE INDEX idx_production_orders_order_id_new ON production_orders(order_id)")
    print("  成功创建新索引!")
except Exception as e:
    print(f"  错误: {e}")

# Now drop the old unique index
print("[2] 删除旧的唯一索引...")
try:
    remote_cursor.execute("DROP INDEX idx_production_orders_order_id ON production_orders")
    print("  成功删除旧索引!")
except Exception as e:
    print(f"  错误: {e}")

# Rename the new index to the original name
print("[3] 重命名索引...")
try:
    remote_cursor.execute("ALTER TABLE production_orders RENAME INDEX idx_production_orders_order_id_new TO idx_production_orders_order_id")
    print("  成功重命名!")
except Exception as e:
    print(f"  错误: {e}")

# Verify
print("\n验证索引...")
remote_cursor.execute("""
    SELECT INDEX_NAME, NON_UNIQUE
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = 'steel_belt'
    AND TABLE_NAME = 'production_orders'
    AND COLUMN_NAME = 'order_id'
""")
for row in remote_cursor.fetchall():
    idx_name, non_unique = row[1], row[3]
    print(f"  索引名: {idx_name}, NON_UNIQUE: {non_unique}")
    if non_unique == 1:
        print("\n✅ 修复成功!")
    else:
        print("\n❌ 仍为唯一索引")

remote_cursor.close()
remote_conn.close()
print("\n完成!")
