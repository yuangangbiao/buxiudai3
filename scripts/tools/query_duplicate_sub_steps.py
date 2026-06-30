import sqlite3, os

db = os.path.join(os.path.dirname(__file__), '..', '..', 'mobile_api_ai', 'wechat_container.db')
db = os.path.normpath(db)
print(f'数据库: {db}')
print()

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute('''
    SELECT process_id, step_name, operator, quantity, DATE(created_at) as dt, COUNT(*) as cnt
    FROM process_sub_steps
    GROUP BY process_id, step_name, operator, quantity, DATE(created_at)
    HAVING cnt > 1
    ORDER BY cnt DESC, dt DESC
''')
groups = cur.fetchall()
if not groups:
    print('无重复报工记录')
else:
    print(f'发现 {len(groups)} 组重复，共涉及 {sum(g["cnt"] for g in groups)} 条记录\n')
    for g in groups:
        print(f'订单: {g["process_id"]}')
        print(f'工序: {g["step_name"]} | 操作人: {g["operator"]} | 数量: {g["quantity"]} | 日期: {g["dt"]} | 重复: {g["cnt"]}次')
        cur.execute('''
            SELECT id, batch_no, created_at FROM process_sub_steps
            WHERE process_id=? AND step_name=? AND operator=? AND quantity=?
              AND DATE(created_at)=?
            ORDER BY created_at
        ''', (g['process_id'], g['step_name'], g['operator'], g['quantity'], g['dt']))
        rows = cur.fetchall()
        for r in rows:
            print(f'    - {r["batch_no"]} | {r["created_at"]}')
        print()
conn.close()
