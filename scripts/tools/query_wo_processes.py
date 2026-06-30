import sqlite3, os

db = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'mobile_api_ai', 'wechat_container.db'))
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

wo = '202605008'

# 查 process_records 表
rows = cur.execute('''
    SELECT id, work_order_no, order_no, product_name, quantity, status, steps
    FROM process_records
    WHERE work_order_no LIKE ? OR order_no LIKE ? OR id LIKE ?
''', (f'%{wo}%', f'%{wo}%', f'%{wo}%')).fetchall()

if rows:
    for r in rows:
        print(f'订单: {r["work_order_no"]}  订单: {r["order_no"]}  产品: {r["product_name"]}')
        print(f'数量: {r["quantity"]}  状态: {r["status"]}')
        print(f'工序列表: {r["steps"]}')
        print()

    # 查报工记录
    for r in rows:
        wid = r['id']
        subs = cur.execute('''
            SELECT step_name, batch_no, quantity, operator, created_at
            FROM process_sub_steps
            WHERE process_id = ?
            ORDER BY created_at
        ''', (wid,)).fetchall()
        print(f'→ 工单 {r["work_order_no"]} 的工序报工 ({len(subs)} 条):')
        for s in subs:
            print(f'   {s["step_name"]} | {s["batch_no"]} | 数量:{s["quantity"]} | {s["operator"]} | {s["created_at"]}')
else:
    print(f'未找到 {wo} 相关记录')

    # 列出所有 WO 工单
    wo_list = cur.execute('''
        SELECT work_order_no FROM process_records
        WHERE work_order_no IS NOT NULL AND work_order_no != ''
        ORDER BY work_order_no
    ''').fetchall()
    print(f'\n现有工单列表:')
    for r in wo_list:
        print(f'  {r["work_order_no"]}')

conn.close()
