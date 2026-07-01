import sqlite3
db = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT DISTINCT process_key FROM order_processes ORDER BY process_key')
keys = cur.fetchall()
print('=== all process keys ===')
for k in keys:
    print('  %s' % k['process_key'])

cur.execute('''
  SELECT op.order_id, op.process_key, op.sequence, ss.quantity, ss.operator, ss.created_at
  FROM order_processes op
  LEFT JOIN sub_steps ss ON ss.order_no = op.order_id AND ss.step_name LIKE '%' || op.process_key || '%'
  WHERE op.order_id = 'CS202604001'
  ORDER BY op.sequence
''')
rows = cur.fetchall()
print('\n=== CS202604001 processes with sub_steps ===')
for r in rows:
    print(dict(r))
conn.close()
