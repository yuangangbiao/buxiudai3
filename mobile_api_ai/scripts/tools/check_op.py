import sqlite3
db = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('PRAGMA table_info(order_processes)')
cols = cur.fetchall()
print('=== order_processes columns ===')
for c in cols:
    print('  %s (%s)' % (c['name'], c['type']))
cur.execute('SELECT * FROM order_processes LIMIT 5')
rows = cur.fetchall()
for r in rows:
    print(dict(r))
cur.execute('SELECT DISTINCT order_id FROM order_processes')
oids = cur.fetchall()
print('\norder_ids:', [r['order_id'] for r in oids])
cur.execute('SELECT order_id, COUNT(*) as cnt FROM order_processes GROUP BY order_id')
counts = cur.fetchall()
for c in counts:
    print('  %s: %d processes' % (c['order_id'], c['cnt']))
conn.close()
