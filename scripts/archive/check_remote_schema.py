# -*- coding: utf-8 -*-
"""检查远程数据库表结构"""

import os
import sys

project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

from db_config import MYSQL_CONFIG
import pymysql

print("=" * 60)
print("远程数据库表结构检查")
print("=" * 60)
print(f"主机: {MYSQL_CONFIG.get('host')}")
print()

try:
    conn = pymysql.connect(
        host=MYSQL_CONFIG.get('host'),
        port=MYSQL_CONFIG.get('port', 3306),
        user=MYSQL_CONFIG.get('user'),
        password=MYSQL_CONFIG.get('password'),
        database=MYSQL_CONFIG.get('database'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

    cursor = conn.cursor()

    # 检查 production_orders 表是否存在
    cursor.execute("SHOW TABLES LIKE 'production_orders'")
    table_exists = cursor.fetchone()

    if not table_exists:
        print("❌ production_orders 表不存在!")
        print()
        print("需要创建以下表:")
        print("  1. production_orders - 生产工单表")
        print("  2. process_records - 工序记录表")
        print()
        print("正在获取本地表结构...")

        # 读取本地SQL文件
        local_sql_file = os.path.join(project_dir, 'data', '工序规则模板.sql')
        if os.path.exists(local_sql_file):
            print(f"找到本地SQL文件: {local_sql_file}")
        else:
            print("未找到本地SQL文件，需要手动创建表结构")
    else:
        print("✓ production_orders 表存在")

        # 检查表字段
        cursor.execute("DESCRIBE production_orders")
        columns = cursor.fetchall()

        print()
        print("production_orders 表结构:")
        print("-" * 50)
        for col in columns:
            print(f"  {col['Field']:30} {col['Type']:20} {col['Null']} {col['Key']}")

        # 检查 process_records 表
        cursor.execute("SHOW TABLES LIKE 'process_records'")
        proc_table_exists = cursor.fetchone()

        print()
        if not proc_table_exists:
            print("❌ process_records 表不存在!")
        else:
            print("✓ process_records 表存在")
            cursor.execute("DESCRIBE process_records")
            proc_columns = cursor.fetchall()
            print()
            print("process_records 表结构:")
            print("-" * 50)
            for col in proc_columns:
                print(f"  {col['Field']:30} {col['Type']:20} {col['Null']} {col['Key']}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"错误: {e}")
