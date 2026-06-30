import sys, os
os.environ["INVENTORY_API_KEY"] = "dev-check"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_connection
from models.enums import ProductionStatus, OrderStatus

conn = get_connection()
cursor = conn.cursor()

print("=== 枚举定义值 ===")
print(f"ProductionStatus.PENDING.value = '{ProductionStatus.PENDING.value}'")
print(f"ProductionStatus.IN_PROGRESS.value = '{ProductionStatus.IN_PROGRESS.value}'")

print("\n=== DB production_orders status值 ===")
cursor.execute("SELECT DISTINCT status FROM production_orders")
for r in cursor.fetchall():
    print(f"  '{r['status']}'")

print("\n=== DB orders status值 ===")
cursor.execute("SELECT DISTINCT status FROM orders")
for r in cursor.fetchall():
    print(f"  '{r['status']}'")

print("\n=== 验证大小写匹配 ===")
default_statuses = ["PENDING", "SCHEDULED", "IN_PROGRESS", "DRAFT", "CONFIRMED"]
print(f"过滤条件(大写): {default_statuses}")

# 查询1: 大写条件
placeholders = ",".join(["%s"] * len(default_statuses))
cursor.execute(f"SELECT COUNT(*) as cnt FROM production_orders WHERE status IN ({placeholders})", default_statuses)
r = cursor.fetchone()
print(f"大写条件匹配: {r['cnt']} 条")

# 查询2: 小写条件
lower_statuses = [s.lower() for s in default_statuses]
cursor.execute(f"SELECT COUNT(*) as cnt FROM production_orders WHERE status IN ({placeholders})", lower_statuses)
r = cursor.fetchone()
print(f"小写条件匹配: {r['cnt']} 条")

# 查询3: 无过滤（总条数）
cursor.execute("SELECT COUNT(*) as cnt FROM production_orders")
r = cursor.fetchone()
print(f"总条数: {r['cnt']} 条")

# 检查 MySQL 排序规则
cursor.execute("SELECT @@collation_connection")
r = cursor.fetchone()
print(f"\nMySQL collation: {r['@@collation_connection']}")

# 检查 status 列排序规则
cursor.execute("SHOW FULL COLUMNS FROM production_orders WHERE Field = 'status'")
r = cursor.fetchone()
print(f"status列 Collation: {r.get('Collation', 'N/A') if r else 'N/A'}")

cursor.execute("SHOW FULL COLUMNS FROM orders WHERE Field = 'status'")
r = cursor.fetchone()
print(f"orders.status列 Collation: {r.get('Collation', 'N/A') if r else 'N/A'}")

cursor.close()
conn.close()
