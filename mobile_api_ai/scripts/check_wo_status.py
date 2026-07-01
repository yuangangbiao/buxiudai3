import sqlite3, json

db_path = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'
db = sqlite3.connect(db_path)
cur = db.cursor()

def print_table(table, where_clause, label):
    print(f'=== {table} {label} ===')
    cur.execute(f'PRAGMA table_info({table})')
    cols = [d[1] for d in cur.fetchall()]
    cur.execute(f'SELECT * FROM {table} WHERE {where_clause}')
    rows = cur.fetchall()
    if not rows:
        print(f'  无记录')
    for r in rows:
        row = dict(zip(cols, r))
        for k, v in row.items():
            if k == 'steps' and isinstance(v, str):
                try:
                    s = json.loads(v)
                    step_names = [x.get('name', str(x)) if isinstance(x,dict) else x for x in (s if isinstance(s,list) else [s])]
                    print(f'  {k}: {step_names}')
                except Exception as e:
                    print(f'  {k}: {v[:100] if v else None} (JSON解析失败: {e})')
            elif k in ('command_data','data','content') and isinstance(v, str) and len(v)>100:
                print(f'  {k}: {v[:200]}...')
            else:
                print(f'  {k}: {v}')
        print()
    return rows

# 检查 WO-202605005
print_table('process_records', "order_no='WO-202605005' OR order_no='WO-202605005'", 'WO-202605005')
print_table('dispatch_commands', "order_no='ORD-202604210003'", 'ORD-202604210003')
print_table('schedule_records', "order_no='ORD-202604210003'", 'ORD-202604210003')

# 对比 WO-202605006
print_table('process_records', "order_no='WO-202605006'", 'WO-202605006')
print_table('dispatch_commands', "order_no='ORD-202604290001'", 'ORD-202604290001')

db.close()

# 检查缓存文件
print('=== dispatch_center_data.json 中的工单 ===')
with open('d:/yuan/不锈钢网带跟单3.0/mobile_api_ai/dispatch_center_data.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)
for p in cache.get('processes', []):
    wo = p.get('order_no','')
    order = p.get('order_no','')
    if '005' in wo or '005' in order or '003' in order:
        print(f'  order_no={wo}')
        print(f'  order_no={order}')
        print(f'  status={p.get("status")}')
        print(f'  current_step={p.get("current_step")}')
        print(f'  source={p.get("source")}')
        print(f'  flow_type={p.get("flow_type")}')
        steps = p.get('steps',[])
        print(f'  steps: {len(steps)}个')
        if steps:
            sn = [s.get('name',str(s)) if isinstance(s,dict) else s for s in steps]
            print(f'  steps_names: {sn}')
        print()
