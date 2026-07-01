# -*- coding: utf-8 -*-
import sqlite3, os, sys
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wechat_container.db')
if not os.path.exists(DB):
    print('DB NOT FOUND: ' + DB)
    sys.exit(1)
conn = sqlite3.connect(DB)
cur = conn.cursor()
print('=== process_records ===')
cur.execute('SELECT id,order_no,work_order_no,product_name,quantity,status FROM process_records LIMIT 20')
for r in cur.fetchall():
    print('|'.join([str(x) if x else '' for x in r[:6]]))
print('=== process_sub_steps ===')
cur.execute('SELECT id,process_id,order_no,step_name,quantity,operator FROM process_sub_steps LIMIT 20')
for r in cur.fetchall():
    print('|'.join([str(x) if x else '' for x in r[:6]]))
conn.close()
