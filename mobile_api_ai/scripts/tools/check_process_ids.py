"""验证 process_records 和 process_sub_steps 的 process_id 一致性"""
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')

db = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
if not os.path.exists(db):
    print(f'数据库不存在: {db}')
    sys.exit(1)

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

order = 'ORD-202604290001'

# 1. process_records
cur.execute('SELECT id, order_no, product_name FROM process_records WHERE order_no = ?', (order,))
rows = cur.fetchall()
print(f'=== process_records ({len(rows)} 条) ===')
for r in rows:
    d = dict(r)
    pid = d['id']
    print(f'  id={pid}')
    
    # 2. process_sub_steps by process_id
    cur2 = conn.cursor()
    cur2.execute('SELECT * FROM process_sub_steps WHERE process_id = ?', (pid,))
    sub_rows = cur2.fetchall()
    print(f'  process_sub_steps (by pid): {len(sub_rows)} 条')
    for s in sub_rows:
        sd = dict(s)
        print(f'    step={sd["step_name"]} qty={sd["quantity"]} batch={sd.get("batch_no","?")}')
    
    # 3. process_sub_steps by order_no
    cur2.execute('SELECT * FROM process_sub_steps WHERE order_no = ?', (order,))
    sub_rows2 = cur2.fetchall()
    print(f'  process_sub_steps (by order_no): {len(sub_rows2)} 条')
    for s in sub_rows2:
        sd = dict(s)
        print(f'    pid={sd["process_id"][:12]} step={sd["step_name"]} qty={sd["quantity"]}')

# 4. 查 dispatch_center_data.json 中的 process_id
dc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'dispatch_center_data.json')
print(f'\n=== dispatch_center_data.json ({dc_path}) ===')
if os.path.exists(dc_path):
    import json
    with open(dc_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for p in data.get('processes', []):
        if order in p.get('order_no', ''):
            print(f'  id={p.get("id","")}')
            print(f'  order_no={p.get("order_no","")}')
            print(f'  step_name={p.get("step_name","")}')
        else:
            pass  # not our order
    # Check if our order exists
    found = any(order in p.get('order_no','') for p in data.get('processes', []))
    if not found:
        print(f'  ❌ {order} 不在 dispatch_center_data.json 中！')
else:
    print(f'  文件不存在')

# 5. 验证 process_records 中实际有多少个不同的 process（按 order_no）
cur.execute('SELECT DISTINCT order_no FROM process_records')
all_orders = [r['order_no'] for r in cur.fetchall()]
print(f'\n=== 所有订单号 ({len(all_orders)} 个) ===')
for o in all_orders:
    cur.execute('SELECT COUNT(*) as cnt FROM process_sub_steps WHERE order_no = ?', (o,))
    cnt = cur.fetchone()['cnt']
    print(f'  {o}: sub_steps={cnt}')

conn.close()
print('\n检查完成')
