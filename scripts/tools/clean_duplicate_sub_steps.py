import sqlite3, os
from datetime import datetime

db = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '..', '..',
    'mobile_api_ai', 'wechat_container.db'
))
print(f'数据库: {db}')

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute('''
    SELECT process_id, step_name, operator, quantity, DATE(created_at) as dt, COUNT(*) as cnt
    FROM process_sub_steps
    GROUP BY process_id, step_name, operator, quantity, DATE(created_at)
    HAVING cnt > 1
    ORDER BY cnt DESC
''')
groups = cur.fetchall()

if not groups:
    print('无重复记录，无需清理')
    conn.close()
    exit(0)

total = sum(g['cnt'] for g in groups)
print(f'发现 {len(groups)} 组重复，共 {total} 条记录\n')

deleted_total = 0
for g in groups:
    cur.execute('''
        SELECT id, batch_no, created_at FROM process_sub_steps
        WHERE process_id=? AND step_name=? AND operator=? AND quantity=?
          AND DATE(created_at)=?
        ORDER BY created_at DESC
    ''', (g['process_id'], g['step_name'], g['operator'], g['quantity'], g['dt']))
    rows = cur.fetchall()

    keep = rows[0]
    ids_to_delete = [r['id'] for r in rows[1:]]
    n = len(ids_to_delete)
    deleted_total += n

    placeholders = ','.join(['?'] * len(ids_to_delete))
    cur.execute(f'DELETE FROM process_sub_steps WHERE id IN ({placeholders})', ids_to_delete)

    print(f'[清理] 订单: {g["process_id"]}')
    print(f'       工序: {g["step_name"]} | 操作人: {g["operator"]} | 数量: {g["quantity"]}')
    print(f'       保留: {keep["batch_no"]} ({keep["created_at"]})')
    print(f'       删除: {n} 条')

conn.commit()
conn.close()
print(f'\n清理完成，共删除 {deleted_total} 条重复记录')
