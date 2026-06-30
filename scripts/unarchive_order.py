# -*- coding: utf-8 -*-
"""
订单取消归档脚本
从归档状态恢复订单到正常状态
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

# 取消归档指定订单
cursor.execute("""
    UPDATE orders
    SET is_archived = 0, status = '已排产', updated_at = NOW()
    WHERE order_no = 'ORD-202605040001'
""")
conn.commit()

print(f"已取消归档: ORD-202605040001")
print(f"影响行数: {cursor.rowcount}")

# 验证更新结果
cursor.execute("SELECT id, order_no, status, is_archived FROM orders WHERE order_no = 'ORD-202605040001'")
order = cursor.fetchone()
print(f"验证: id={order['id']}, order_no={order['order_no']}, status={order['status']}, is_archived={order['is_archived']}")

conn.close()
print("\n完成！")