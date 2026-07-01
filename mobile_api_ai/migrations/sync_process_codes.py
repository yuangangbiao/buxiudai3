# -*- coding: utf-8 -*-
"""
同步修复订单 process_code 分类

根据新分类规则修正历史数据：
1. PXAEAA（step_name=入库）→ STOCK_IN
2. 其他 PX*/N/A/DBG 测试码 → 保持忽略（不修改）

运行：
    python migrations/sync_process_codes.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from datetime import datetime


def get_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='88888888',
        database='container_center',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def main():
    conn = get_connection()
    cursor = conn.cursor()

    print('=' * 60)
    print('同步修复 process_code 分类')
    print('=' * 60)

    # 1. 修复 PXAEAA → STOCK_IN（step_name=入库）
    print()
    print('[1] 修复 PXAEAA → STOCK_IN')
    cursor.execute("""
        SELECT id, process_code, step_name, quantity, completed_qty
        FROM process_sub_steps
        WHERE process_code = 'PXAEAA'
    """)
    px_row = cursor.fetchone()
    if px_row:
        print(f'  找到: id={px_row["id"]}, code={px_row["process_code"]}, step={px_row["step_name"]}')

        # 检查是否已存在 STOCK_IN
        cursor.execute("""
            SELECT id, process_code, step_name
            FROM process_sub_steps
            WHERE process_code = 'STOCK_IN'
        """)
        existing = cursor.fetchone()

        if existing:
            print(f'  已存在 STOCK_IN: id={existing["id"]}')
            px_qty = px_row.get('quantity') or 0
            ex_qty = existing.get('quantity') or 0
            print(f'  合并数量: PXAEAA({px_qty}) + STOCK_IN({ex_qty})')
            # 更新 PXAEAA 的数量到 STOCK_IN，然后删除 PXAEAA
            new_qty = px_qty + ex_qty
            cursor.execute("""
                UPDATE process_sub_steps
                SET quantity = %s, process_code = 'STOCK_IN'
                WHERE id = %s
            """, (new_qty, px_row['id']))
            print(f'  更新 PXAEAA → STOCK_IN, qty={new_qty}')
        else:
            # 直接改 process_code
            cursor.execute("""
                UPDATE process_sub_steps
                SET process_code = 'STOCK_IN'
                WHERE id = %s
            """, (px_row['id'],))
            print(f'  直接更新: PXAEAA → STOCK_IN')

    # 2. 统计修正后的分布
    print()
    print('[2] 修正后 process_code 分布')
    cursor.execute("""
        SELECT process_code,
               CASE
                   WHEN process_code LIKE 'P%' THEN 'production'
                   WHEN process_code LIKE 'M%' THEN 'material_purchase'
                   WHEN process_code LIKE 'Q%' THEN 'quality'
                   WHEN process_code = 'STOCK_IN' THEN 'warehousing'
                   ELSE 'ignored'
               END as flow_type,
               COUNT(*) as cnt
        FROM process_sub_steps
        WHERE process_code IS NOT NULL AND process_code != ''
        GROUP BY process_code
        ORDER BY
            CASE WHEN process_code LIKE 'P%' THEN 1
                 WHEN process_code LIKE 'M%' THEN 2
                 WHEN process_code LIKE 'Q%' THEN 3
                 WHEN process_code = 'STOCK_IN' THEN 4
                 ELSE 5 END,
            process_code
    """)

    print(f'  {'码':<12} {'类型':<20} {'数量':<6}')
    print('  ' + '-' * 40)
    for row in cursor.fetchall():
        print(f'  {row["process_code"]:<12} {row["flow_type"]:<20} {row["cnt"]:<6}')

    conn.commit()
    cursor.close()
    conn.close()

    print()
    print('=' * 60)
    print('同步完成')
    print('=' * 60)


if __name__ == '__main__':
    main()
