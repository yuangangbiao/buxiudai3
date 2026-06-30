# -*- coding: utf-8 -*-
"""检查 192.168.0.101 数据库"""

import os
import sys

project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

import pymysql

REMOTE_HOST = '192.168.0.101'
REMOTE_PORT = 3306
REMOTE_USER = 'root'
REMOTE_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')

print("=" * 60)
print("检查 192.168.0.101 数据库")
print("=" * 60)

try:
    print("1. 测试连接...")
    conn = pymysql.connect(
        host=REMOTE_HOST,
        port=REMOTE_PORT,
        user=REMOTE_USER,
        password=REMOTE_PASSWORD,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10
    )
    print("   ✓ 连接成功!")

    cursor = conn.cursor()

    print("2. 获取数据库列表...")
    cursor.execute("SHOW DATABASES")
    dbs = cursor.fetchall()
    for db in dbs:
        print(f"   - {list(db.values())[0]}")

    print("3. 选择 steel_belt 数据库...")
    cursor.execute("USE steel_belt")
    print("   ✓ 切换成功!")

    print("4. 获取表列表...")
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print(f"   数据库中的表 ({len(tables)} 个):")
    for t in tables:
        print(f"   - {list(t.values())[0]}")

    print()
    print("5. 检查 production_orders 表...")
    cursor.execute("SHOW TABLES LIKE 'production_orders'")
    if not cursor.fetchone():
        print("   ❌ production_orders 表不存在!")
    else:
        print("   ✓ production_orders 表存在")
        cursor.execute("DESCRIBE production_orders")
        cols = cursor.fetchall()
        print(f"   字段数: {len(cols)}")
        for col in cols:
            print(f"     {col['Field']:30} {col['Type']}")

    cursor.close()
    conn.close()
    print()
    print("检查完成!")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
