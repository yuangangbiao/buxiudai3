# -*- coding: utf-8 -*-
"""
补充 MySQL production_orders 表的 order_no 字段
从 SQLite wechat_container.db 读取数据匹配
"""
import os
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pymysql
    from pymysql.cursors import DictCursor
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print('[ERROR] pymysql 未安装')

MYSQL_CFG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', '88888888'),
    'database': os.environ.get('MYSQL_DATABASE', 'steel_belt'),
    'charset': 'utf8mb4',
}

SQLITE_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'wechat_container.db')

def get_sqlite_work_order_mapping():
    """从 SQLite 读取 order_no -> order_no 映射"""
    if not os.path.exists(SQLITE_DB):
        print(f'[WARN] SQLite 数据库不存在: {SQLITE_DB}')
        return {}

    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT order_no, order_no
        FROM process_records
        WHERE order_no IS NOT NULL AND order_no != ''
        GROUP BY order_no
    """)
    rows = cur.fetchall()
    conn.close()

    result = {}
    for row in rows:
        if row['order_no']:
            result[row['order_no']] = row['order_no']
    return result

def fix_mysql_work_order_no():
    """修复 MySQL production_orders 表的 order_no"""
    if not MYSQL_AVAILABLE:
        return

    wo_mapping = get_sqlite_work_order_mapping()
    print(f'[INFO] 从 SQLite 获取到 {len(wo_mapping)} 个订单号映射')
    for k, v in list(wo_mapping.items())[:5]:
        print(f'  SQLite: order_no={k} -> order_no={v}')

    conn = pymysql.connect(**MYSQL_CFG, cursorclass=DictCursor, connect_timeout=10)
    cur = conn.cursor()

    cur.execute("SELECT id, order_no, order_id FROM production_orders WHERE is_deleted=0")
    rows = cur.fetchall()

    print(f'[INFO] production_orders 表共有 {len(rows)} 条记录')

    updated = 0
    for row in rows:
        po_id = row['id']
        current_wo_no = row['order_no']
        order_id = row['order_id']

        if current_wo_no and str(current_wo_no).strip():
            continue

        if not order_id:
            continue

        cur.execute("SELECT order_no FROM orders WHERE id=%s", (order_id,))
        order_row = cur.fetchone()
        if not order_row:
            continue

        order_no = order_row['order_no']

        if order_no in wo_mapping:
            new_wo_no = wo_mapping[order_no]
            cur.execute(
                "UPDATE production_orders SET order_no=%s WHERE id=%s",
                (new_wo_no, po_id)
            )
            updated += 1
            print(f'[UPDATE] id={po_id}, order_id={order_id}, order_no={order_no} -> order_no={new_wo_no}')

    conn.commit()
    print(f'[DONE] 共更新 {updated} 条记录')

    cur.execute("SELECT COUNT(*) as cnt FROM production_orders WHERE (order_no IS NULL OR order_no = '') AND is_deleted=0")
    remaining = cur.fetchone()['cnt']
    print(f'[INFO] 剩余 order_no 为空的记录: {remaining}')

    conn.close()

if __name__ == '__main__':
    print('=' * 60)
    print('补充 MySQL production_orders 表的 order_no')
    print('=' * 60)
    fix_mysql_work_order_no()
