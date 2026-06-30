# -*- coding: utf-8 -*-
"""T1.0: 检查并执行 DDL,验证 order_status_contract.py"""
import sys
import os

# 项目根目录加入 sys.path
PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from models.database import get_connection

def run():
    conn = get_connection()
    cur = conn.cursor()
    target = 'last_status_update_at'

    # 1. 检查字段是否存在
    cur.execute('SHOW COLUMNS FROM orders')
    cols = {r['Field'] for r in cur.fetchall()}
    print(f'[1] 字段存在: {target in cols}')

    if target not in cols:
        # 2. 执行 DDL
        print('[2] 执行 ALTER TABLE ADD COLUMN...')
        cur.execute(
            'ALTER TABLE orders ADD COLUMN last_status_update_at '
            'DATETIME DEFAULT CURRENT_TIMESTAMP '
            'ON UPDATE CURRENT_TIMESTAMP '
            'AFTER updated_at'
        )
        conn.commit()
        print('[3] DDL 成功')

        # 3. 回填
        cur.execute(
            'SELECT COUNT(*) as cnt FROM orders WHERE last_status_update_at IS NULL'
        )
        null_cnt = cur.fetchone()['cnt']
        print(f'[4] 回填前 NULL 行数: {null_cnt}')
        if null_cnt > 0:
            cur.execute(
                'UPDATE orders SET last_status_update_at = updated_at '
                'WHERE last_status_update_at IS NULL'
            )
            conn.commit()
            print(f'[5] 回填完成: {null_cnt} 行')

        # 4. 验证
        cur.execute('SHOW COLUMNS FROM orders')
        cols2 = {r['Field'] for r in cur.fetchall()}
        print(f'[6] 验证字段存在: {target in cols2}')
    else:
        print('[2] 字段已存在,跳过 DDL')

    conn.close()
    print('[OK] T1.0 完成: 数据库就绪')

if __name__ == '__main__':
    run()
