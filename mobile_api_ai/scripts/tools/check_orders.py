import sqlite3
db = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('PRAGMA table_info(orders)')
cols = cur.fetchall()
print('=== orders columns ===')
for c in cols:
    print('  %s (%s)' % (c['name'], c['type']))
cur.execute('SELECT * FROM orders')
rows = cur.fetchall()
print('\n=== %d orders ===' % len(rows))
for r in rows:
    d = dict(r)
    print('  %s: status=%s, priority=%s, delivery=%s' % (d['order_id'], d.get('status'), d.get('priority'), d.get('delivery_date')))
conn.close()
