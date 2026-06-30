# -*- coding: utf-8 -*-
"""
订单检查脚本
查看最近10条订单及其额外参数
用于检查订单数据结构
"""
import sys
import os
import json

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_DIR, '.env'))

print("当前数据库配置:")
print(f"  MYSQL_HOST: {os.getenv('MYSQL_HOST')}")
print(f"  MYSQL_PORT: {os.getenv('MYSQL_PORT')}")
print(f"  MYSQL_DATABASE: {os.getenv('MYSQL_DATABASE')}")

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
# 查询最近10条订单
cursor.execute("SELECT id, order_no, extra_params FROM orders ORDER BY id DESC LIMIT 10")
orders = cursor.fetchall()

# 保存到文件
with open('d:/yuan/all_orders.txt', 'w', encoding='utf-8') as f:
    f.write("最近的订单:\n")
    for o in orders:
        f.write(f"\nID: {o['id']}, 订单号: {o['order_no']}\n")
        extra = {}
        if o['extra_params']:
            try:
                extra = json.loads(o['extra_params']) if isinstance(o['extra_params'], str) else o['extra_params']
            except Exception as e:
                print(f"[check_all_orders] 解析订单 {o['order_no']} extra_params失败: {e}")
                extra = {}
        f.write(f"  参数: {list(extra.keys())}\n")
        if '总长度' in extra:
            f.write(f"  总长度: {extra['总长度']}\n")

conn.close()
print("\n结果已保存到 d:/yuan/all_orders.txt")