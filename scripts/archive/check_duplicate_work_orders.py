# -*- coding: utf-8 -*-
"""检查重复工单 - 直接连接"""

import os
import sys

# 添加项目路径
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# 导入环境变量
from db_config import MYSQL_CONFIG
import pymysql

print("=" * 60)
print("重复工单检查")
print("=" * 60)

try:
    # 直接连接MySQL
    conn = pymysql.connect(
        host=MYSQL_CONFIG.get('host', 'localhost'),
        port=MYSQL_CONFIG.get('port', 3306),
        user=MYSQL_CONFIG.get('user', 'root'),
        password=MYSQL_CONFIG.get('password', ''),
        database=MYSQL_CONFIG.get('database', 'steel_belt'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

    cursor = conn.cursor()

    # 查找重复工单
    cursor.execute("""
        SELECT order_id, COUNT(*) as cnt, GROUP_CONCAT(id) as prod_ids
        FROM production_orders
        GROUP BY order_id
        HAVING cnt > 1
    """)
    duplicates = cursor.fetchall()

    if duplicates:
        print(f"发现 {len(duplicates)} 组重复订单:")
        print()
        for d in duplicates:
            print(f"  订单ID: {d['order_id']}")
            print(f"  工单数量: {d['cnt']}")
            print(f"  工单ID列表: {d['prod_ids']}")

            cursor.execute("""
                SELECT id, work_order_no, status, created_at
                FROM production_orders
                WHERE order_id = %s
            """, (d['order_id'],))
            details = cursor.fetchall()
            for detail in details:
                print(f"    - ID={detail['id']}, 订单号={detail['work_order_no']}, 状态={detail['status']}, 创建时间={detail['created_at']}")
            print()
    else:
        print("没有发现重复工单")

    # 工单统计
    cursor.execute("SELECT COUNT(*) as total, COUNT(DISTINCT order_id) as unique_orders FROM production_orders")
    stats = cursor.fetchone()
    print("=" * 60)
    print("工单统计")
    print("=" * 60)
    print(f"  工单总数: {stats['total']}")
    print(f"  涉及订单数: {stats['unique_orders']}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"数据库连接失败: {e}")
    print(f"当前配置: host={MYSQL_CONFIG.get('host')}, port={MYSQL_CONFIG.get('port')}")
