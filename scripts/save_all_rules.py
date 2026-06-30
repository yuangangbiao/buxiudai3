# -*- coding: utf-8 -*-
"""
规则导出脚本
导出弹簧网的所有物料规则到文件
检查公式中的特殊数值
"""
import sys
import os

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

# 检查弹簧网的所有物料规则
cursor.execute("""
    SELECT id, product_type, material_param, material_name_template,
           qty_formula, enabled
    FROM material_rules
    WHERE product_type = '弹簧网'
    ORDER BY id
""")
rules = cursor.fetchall()

with open('d:/yuan/all_rules.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("弹簧网的所有物料规则:\n")
    f.write("=" * 80 + "\n")
    for r in rules:
        f.write(f"\nID: {r['id']}\n")
        f.write(f"  材质参数: {r['material_param']}\n")
        f.write(f"  物料名称模板: {r['material_name_template']}\n")
        f.write(f"  启用: {r['enabled']}\n")
        f.write(f"  公式: {r['qty_formula']}\n")

    # 检查是否有其他产品类型的规则用了0.000623
    f.write("\n" + "=" * 80 + "\n")
    f.write("检查所有包含 '0.000' 的公式:\n")
    f.write("=" * 80 + "\n")
    cursor.execute("""
        SELECT id, product_type, material_param, qty_formula
        FROM material_rules
        WHERE qty_formula LIKE '%0.000%'
    """)
    bad_rules = cursor.fetchall()
    for r in bad_rules:
        f.write(f"\nID: {r['id']}, 产品类型: {r['product_type']}\n")
        f.write(f"  材质参数: {r['material_param']}\n")
        f.write(f"  公式: {r['qty_formula']}\n")

conn.close()
print("结果已保存到 d:/yuan/all_rules.txt")