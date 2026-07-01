# -*- coding: utf-8 -*-
"""检查 MySQL process_records 表的数据情况"""
import os
import sys

try:
    import pymysql
    from pymysql.cursors import DictCursor
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

MYSQL_CFG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '88888888',
    'database': 'steel_belt',
    'charset': 'utf8mb4',
}

def main():
    if not MYSQL_AVAILABLE:
        print('[ERROR] pymysql 未安装')
        return

    conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor, connect_timeout=10)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, production_id, process_name, process_seq, planned_qty, completed_qty, status
        FROM process_records
        ORDER BY production_id, process_seq
        LIMIT 50
    """)
    rows = cur.fetchall()

    print(f'process_records 表数据 (前50条):')
    print(f'{'ID':<5} {'production_id':<15} {'process_name':<20} {'seq':<5} {'plan':<8} {'done':<8} {'status':<10}')
    print('-' * 80)
    for row in rows:
        print(f"{row['id']:<5} {str(row['production_id']):<15} {str(row['process_name']):<20} {row['process_seq']:<5} {row['planned_qty']:<8} {row['completed_qty']:<8} {row['status']:<10}")

    print()
    cur.execute("SELECT COUNT(*) as cnt FROM process_records")
    total = cur.fetchone()['cnt']
    print(f'process_records 表总记录数: {total}')

    cur.execute("SELECT COUNT(DISTINCT production_id) as cnt FROM process_records WHERE production_id IS NOT NULL")
    distinct_prod = cur.fetchone()['cnt']
    print(f'涉及的生产工单数: {distinct_prod}')

    conn.close()

if __name__ == '__main__':
    main()
