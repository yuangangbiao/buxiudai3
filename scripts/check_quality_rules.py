# -*- coding: utf-8 -*-
"""
质检规则检查脚本
查看现有的质检规则和最近的质检记录
用于了解质检配置和查看历史记录
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

# 查看质检规则
print("=== 现有质检规则 ===")
cursor.execute("SELECT * FROM quality_rules WHERE enabled=1")
rules = cursor.fetchall()
for r in rules:
    print(f"\n规则ID: {r['id']}")
    print(f"  规则名称: {r['rule_name']}")
    print(f"  工序: {r['process_name']}")
    print(f"  产品类型: {r['product_types_json']}")
    print(f"  质检项目: {r['inspection_items_json']}")

# 查看最近5条质检记录
print("\n\n=== 现有质检记录示例 ===")
cursor.execute("SELECT * FROM quality_records ORDER BY id DESC LIMIT 5")
records = cursor.fetchall()
for r in records:
    print(f"\n记录ID: {r['id']}")
    print(f"  订单ID: {r['order_id']}")
    print(f"  工序: {r['process_name']}")
    print(f"  质检类型: {r['inspection_type']}")
    print(f"  结果: {r['result']}")

conn.close()