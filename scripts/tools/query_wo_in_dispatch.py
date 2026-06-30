import sqlite3, os, json

db = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'mobile_api_ai', 'wechat_container.db'))
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# dispatch_commands 中所有 order_no 含 WO 的
cur.execute('''
    SELECT id, command_id, order_no, process_name, operator_id, target_id, status, command_data, created_at
    FROM dispatch_commands
    WHERE order_no LIKE '%WO%' OR order_no LIKE 'WO%'
    ORDER BY created_at
''')
rows = cur.fetchall()
print(f'dispatch_commands 中含 WO 的记录: {len(rows)} 条\n')
if rows:
    for r in rows:
        print(f'  ID={r["id"]} | {r["order_no"]} | 工序:{r["process_name"]} | 操作人:{r["operator_id"]} | {r["created_at"]}')
else:
    print('无 WO 记录')

# 查看 command_data 中是否含 work_order_no
print('\n--- 查看 command_data 内容（前3条） ---')
for r in cur.execute('SELECT order_no, command_data FROM dispatch_commands LIMIT 3').fetchall():
    print(f'  order_no={r["order_no"]} | data={r["command_data"]}')

# process_records 中 WO 工单
print('\n=== process_records 中的 WO 工单 ===')
cur.execute('''
    SELECT work_order_no, order_no, product_name, quantity, status, steps
    FROM process_records
    WHERE work_order_no IS NOT NULL AND work_order_no != ''
    ORDER BY work_order_no
''')
wos = cur.fetchall()
if wos:
    print(f'共 {len(wos)} 个工单：')
    for r in wos:
        steps = r['steps']
        if steps and isinstance(steps, str):
            try:
                step_list = json.loads(steps)
                step_names = [s.get('name', '') for s in step_list]
            except:
                step_names = ['(解析失败)']
        else:
            step_names = []
        print(f'  {r["work_order_no"]} | 订单:{r["order_no"]} | 产品:{r["product_name"]} | 数量:{r["quantity"]} | 状态:{r["status"]}')
        print(f'    工序: {", ".join(step_names)}')
else:
    print('无记录')

conn.close()
