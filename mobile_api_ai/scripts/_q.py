# -*- coding: utf-8 -*-
import sqlite3, os
DB = 'D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'
OUT = 'D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/scripts/_q_out.txt'
lines = []
try:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    lines.append('=== process_records ===')
    cur.execute('SELECT id,order_no,work_order_no,product_name,quantity,status FROM process_records LIMIT 20')
    for r in cur.fetchall():
        lines.append('|'.join([str(x) if x else '' for x in r[:6]]))
    lines.append('=== process_sub_steps ===')
    cur.execute('SELECT id,process_id,order_no,step_name,quantity,operator FROM process_sub_steps LIMIT 20')
    for r in cur.fetchall():
        lines.append('|'.join([str(x) if x else '' for x in r[:6]]))
    conn.close()
except Exception as e:
    lines.append('ERROR: ' + str(e))
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
