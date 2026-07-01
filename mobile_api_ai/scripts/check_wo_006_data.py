# -*- coding: utf-8 -*-
"""WO-202605006 完整数据"""
import sqlite3, json, os, sys, subprocess

# 确保 UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
elif hasattr(sys.stdout, 'buffer'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

db_path = 'd:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'

db = sqlite3.connect(db_path)
cur = db.cursor()

# 1. process_records
cur.execute('SELECT * FROM process_records WHERE order_no=?', ('WO-202605006',))
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
if rows:
    d = dict(zip(cols, rows[0]))
    for k in ['id','order_no','order_no','product_name','customer_name',
              'quantity','unit','status','current_step','flow_type','source',
              'created_at','updated_at','steps']:
        v = d.get(k, '')
        if k == 'steps' and v:
            try:
                s = json.loads(v) if isinstance(v, str) else v
                print(f'{k}: {json.dumps(s, ensure_ascii=False)[:600]}')
            except Exception as e:
                print(f'{k}: {v} (JSON解析失败: {e})')
        else:
            print(f'{k}: {v}')
else:
    print('process_records not found')

# 2. 看看有哪些 order_no 关联
print('\n--- ORD-202604290001 的 data_packages ---')
cur.execute('SELECT related_process FROM data_packages WHERE related_order=?', ('WO-202605006',))
for r in cur.fetchall():
    print(f'  工序: {r[0]}')

# 3. dispatch_commands
print('\n--- dispatch_commands ---')
cur.execute("SELECT process_name, quantity, status FROM dispatch_commands WHERE order_no='ORD-202604290001'")
for r in cur.fetchall():
    print(f'  工序: {r[0]}, 数量: {r[1]}, 状态: {r[2]}')

db.close()
