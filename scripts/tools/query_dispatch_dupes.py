import sqlite3, os
from collections import Counter

db = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'mobile_api_ai', 'wechat_container.db'))
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print('=== dispatch_commands 列结构 ===')
cols = [d['name'] for d in cur.execute('PRAGMA table_info(dispatch_commands)').fetchall()]
print(f'列: {cols}\n')

# 查同 order_no + process_name 的重复组
cur.execute('''
    SELECT order_no, process_name, COUNT(*) as cnt
    FROM dispatch_commands
    WHERE order_no IS NOT NULL AND order_no != ''
      AND process_name IS NOT NULL AND process_name != ''
    GROUP BY order_no, process_name
    HAVING cnt > 1
    ORDER BY cnt DESC
''')
groups = cur.fetchall()

if not groups:
    print('无重复：没有同工单+同工序的 dispatch_commands 记录\n')

    # 显示所有 order_no+process_name 组合
    cur.execute('''
        SELECT order_no, process_name, COUNT(*) as cnt
        FROM dispatch_commands
        WHERE order_no IS NOT NULL AND order_no != ''
        GROUP BY order_no, process_name
        ORDER BY order_no, process_name
    ''')
    all_groups = cur.fetchall()
    print(f'共有 {len(all_groups)} 组工单+工序组合：')
    for g in all_groups:
        print(f'  {g["order_no"]} | {g["process_name"]} | {g["cnt"]}条')
else:
    total_dup = sum(g['cnt'] for g in groups)
    print(f'发现 {len(groups)} 组重复，共涉及 {total_dup} 条记录\n')
    for g in groups:
        print(f'订单: {g["order_no"]} | 工序: {g["process_name"]} | 重复: {g["cnt"]}次')
        cur.execute('''
            SELECT command_id, command_type, target_id, operator_id, status, created_at, command_data
            FROM dispatch_commands
            WHERE order_no=? AND process_name=?
            ORDER BY created_at
        ''', (g['order_no'], g['process_name']))
        rows = cur.fetchall()
        for r in rows:
            print(f'    {r["command_id"]} | type={r["command_type"]} | target={r["target_id"]} | operator={r["operator_id"]} | status={r["status"]} | {r["created_at"]}')
        print()

conn.close()
