# -*- coding: utf-8 -*-
"""
规则检查脚本
查看所有产品类型、物料计算规则和工序计算规则
用于快速了解系统配置的所有计算规则
"""
import sys
import os
import json

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_DIR, '.env'))

import pymysql

# 建立数据库连接
conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database=os.getenv('MYSQL_DATABASE', 'steel_belt'),
    charset='utf8mb4'
)

cursor = conn.cursor(pymysql.cursors.DictCursor)

# 获取所有产品类型
print("=== 所有产品类型 ===")
cursor.execute("SELECT id, product_type FROM product_types")
product_types = cursor.fetchall()
for pt in product_types:
    print(f"  {pt['id']}: {pt['product_type']}")

# 获取物料计算规则
print("\n=== 物料计算规则 ===")
cursor.execute("SELECT id, product_type, formula, material_name FROM material_rules WHERE enabled=1")
material_rules = cursor.fetchall()
for rule in material_rules:
    print(f"\n产品类型: {rule['product_type']}")
    print(f"物料名称: {rule['material_name']}")
    print(f"计算公式: {rule['formula']}")

# 获取工序计算规则
print("\n=== 工序计算规则 ===")
cursor.execute("SELECT id, process_name, product_types_json, planned_qty_formula FROM process_calc_rules WHERE enabled=1")
process_rules = cursor.fetchall()
for rule in process_rules:
    print(f"\n工序名称: {rule['process_name']}")
    print(f"适用产品: {rule['product_types_json']}")
    print(f"计算公式: {rule['planned_qty_formula']}")

conn.close()