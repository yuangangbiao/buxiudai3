# -*- coding: utf-8 -*-
"""
检查数据库中公式的原始存储
"""
import sys
import os

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
cursor.execute("""
    SELECT id, product_type, material_param, qty_formula,
           LENGTH(qty_formula) as formula_len,
           LOCATE('0.00', qty_formula) as zero_pos,
           SUBSTRING(qty_formula, LOCATE('0.00', qty_formula), 20) as formula_part
    FROM material_rules
    WHERE product_type = '弹簧网' AND enabled = 1
""")
rule = cursor.fetchone()

print("数据库原始数据:")
print(f"ID: {rule['id']}")
print(f"产品类型: {rule['product_type']}")
print(f"材质参数: {rule['material_param']}")
print(f"公式长度: {rule['formula_len']}")
print(f"公式内容: [{rule['qty_formula']}]")
print()
print("公式逐字符分析:")
for i, c in enumerate(rule['qty_formula']):
    print(f"  [{i:3}] {repr(c)}")

conn.close()