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
    connect_timeout=30
)
print("连接成功!")

remote_cursor = remote_conn.cursor()

print("\n[1/6] 禁用外键检查...")
remote_cursor.execute("SET FOREIGN_KEY_CHECKS=0")

print("[2/6] 删除 process_records 外键...")
try:
    remote_cursor.execute("ALTER TABLE process_records DROP FOREIGN KEY process_records_ibfk_2")
    print("  已删除 process_records_ibfk_2")
except Exception as e:
    print(f"  跳过或错误: {e}")

print("[3/6] 删除 production_stats 外键...")
try:
    remote_cursor.execute("ALTER TABLE production_stats DROP FOREIGN KEY production_stats_ibfk_2")
    print("  已删除 production_stats_ibfk_2")
except Exception as e:
    print(f"  跳过或错误: {e}")

print("[4/6] 删除 quality_records 外键...")
try:
    remote_cursor.execute("ALTER TABLE quality_records DROP FOREIGN KEY quality_records_ibfk_2")
    print("  已删除 quality_records_ibfk_2")
except Exception as e:
    print(f"  跳过或错误: {e}")

print("[5/6] 删除唯一索引并创建普通索引...")
try:
    remote_cursor.execute("DROP INDEX idx_production_orders_order_id ON production_orders")
    print("  已删除唯一索引")
except Exception as e:
    print(f"  删除索引错误: {e}")

try:
    remote_cursor.execute("CREATE INDEX idx_production_orders_order_id ON production_orders(order_id)")
    print("  已创建普通索引")
except Exception as e:
    print(f"  创建索引错误: {e}")

print("[6/6] 重新创建外键...")
try:
    remote_cursor.execute("ALTER TABLE process_records ADD CONSTRAINT process_records_ibfk_2 FOREIGN KEY (production_id) REFERENCES production_orders(id)")
    print("  已创建 process_records_ibfk_2")
except Exception as e:
    print(f"  创建 process_records_ibfk_2 错误: {e}")

try:
    remote_cursor.execute("ALTER TABLE production_stats ADD CONSTRAINT production_stats_ibfk_2 FOREIGN KEY (production_id) REFERENCES production_orders(id)")
    print("  已创建 production_stats_ibfk_2")
except Exception as e:
    print(f"  创建 production_stats_ibfk_2 错误: {e}")

try:
    remote_cursor.execute("ALTER TABLE quality_records ADD CONSTRAINT quality_records_ibfk_2 FOREIGN KEY (production_id) REFERENCES production_orders(id)")
    print("  已创建 quality_records_ibfk_2")
except Exception as e:
    print(f"  创建 quality_records_ibfk_2 错误: {e}")

print("\n[完成] 启用外键检查...")
remote_cursor.execute("SET FOREIGN_KEY_CHECKS=1")

print("\n验证索引类型...")
remote_cursor.execute("""
    SELECT INDEX_NAME, NON_UNIQUE
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = 'steel_belt'
    AND TABLE_NAME = 'production_orders'
    AND INDEX_NAME = 'idx_production_orders_order_id'
""")
result = remote_cursor.fetchone()
if result:
    print(f"索引名: {result[0]}, NON_UNIQUE: {result[1]}")
    if result[1] == 1:
        print("\n✅ 修复成功! 现在一个订单可以创建多个工单了。")
    else:
        print("\n❌ 修复失败，索引仍然是唯一的。")
else:
    print("索引不存在")

remote_cursor.close()
remote_conn.close()
print("\n完成!")
