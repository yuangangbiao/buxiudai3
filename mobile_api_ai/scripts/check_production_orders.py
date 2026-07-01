# -*- coding: utf-8 -*-
"""查询 MySQL production_orders 表的 order_no 情况"""
import os
import sys

try:
    import pymysql
    from pymysql.cursors import DictCursor
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

MYSQL_CFG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4',
}

def main():
    if not MYSQL_AVAILABLE:
        print('[ERROR] pymysql 未安装')
        return

    conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor, connect_timeout=10)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, order_no, order_id, status, is_deleted
        FROM production_orders
        WHERE is_deleted=0
        ORDER BY id
    """)
    rows = cur.fetchall()

    print(f'{'ID':<5} {'order_no':<25} {'order_id':<10} {'status':<10}')
    print('-' * 60)
    for row in rows:
        print(f"{row['id']:<5} {str(row['order_no']):<25} {str(row['order_id']):<10} {row['status']:<10}")

    print()
    cur.execute("SELECT COUNT(*) as cnt FROM production_orders WHERE (order_no IS NULL OR order_no = '') AND is_deleted=0")
    empty = cur.fetchone()['cnt']
    print(f'order_no 为空: {empty} 条')

    conn.close()

if __name__ == '__main__':
    main()
