# -*- coding: utf-8 -*-
import sys
import os
import json

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_DIR, '.env'))

import pymysql

conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database=os.getenv('MYSQL_DATABASE', 'steel_belt'),
    charset='utf8mb4'
)

cursor = conn.cursor(pymysql.cursors.DictCursor)

# 检查表结构
print("=== product_types 表结构 ===")
cursor.execute("DESCRIBE product_types")
cols = cursor.fetchall()
for c in cols:
    print(f"  {c['Field']}: {c['Type']}")

print("\n=== material_rules 表结构 ===")
cursor.execute("DESCRIBE material_rules")
cols = cursor.fetchall()
for c in cols:
    print(f"  {c['Field']}: {c['Type']}")

print("\n=== process_calc_rules 表结构 ===")
cursor.execute("DESCRIBE process_calc_rules")
cols = cursor.fetchall()
for c in cols:
    print(f"  {c['Field']}: {c['Type']}")

conn.close()