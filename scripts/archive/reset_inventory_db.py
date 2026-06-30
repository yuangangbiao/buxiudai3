# -*- coding: utf-8 -*-
"""重新初始化库存数据库"""
import pymysql
from pymysql.cursors import DictCursor
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from db_config import MYSQL_CONFIG
except ImportError:
    MYSQL_CONFIG = {
        "host": os.getenv('MYSQL_HOST', 'localhost'),
        "port": int(os.getenv('MYSQL_PORT', 3306)),
        "user": os.getenv('MYSQL_USER', 'root'),
        "password": os.getenv('MYSQL_PASSWORD', ''),
        "charset": "utf8mb4"
    }

INVENTORY_DB_CONFIG = {
    "host": MYSQL_CONFIG['host'],
    "port": MYSQL_CONFIG.get('port', 3306),
    "user": MYSQL_CONFIG['user'],
    "password": MYSQL_CONFIG['password'],
    "database": "inventory_management_db",
    "charset": "utf8mb4"
}

print("=" * 60)
print("  重新初始化库存数据库")
print("=" * 60)
print()

print("[1] 清理旧数据...")
conn = pymysql.connect(**INVENTORY_DB_CONFIG)
cursor = conn.cursor()
try:
    cursor.execute('DELETE FROM inventory_transactions')
    cursor.execute('DELETE FROM inventory')
    cursor.execute('DELETE FROM products')
    conn.commit()
    print("    OK - 旧数据已清理")
except Exception as e:
    print(f"    警告: {e}")
cursor.close()
conn.close()

print("[2] 重新插入初始数据...")
from inventory_db_complete import InventoryDB, inv_db
db = InventoryDB()
db.insert_initial_data()
print("    OK")

print("[3] 验证数据...")
stats = inv_db.get_statistics()
print(f"    商品种类: {stats['product_count']}")
print(f"    库存总量: {stats['total_qty']}")
print(f"    库存总值: {stats['total_value']}")
print(f"    低库存预警: {stats['low_stock_count']}")

inventory = inv_db.get_all_inventory()
print(f"    库存记录数: {len(inventory)}")

if inventory:
    print()
    print("[4] 示例库存数据:")
    for inv in inventory[:5]:
        sku = inv.get('sku', '')
        name = str(inv.get('product_name', ''))[:20]
        qty = inv.get('current_qty', 0)
        print(f"    {sku} | {name} | 库存: {qty}")

print()
print("=" * 60)
print("  初始化完成!")
print("=" * 60)