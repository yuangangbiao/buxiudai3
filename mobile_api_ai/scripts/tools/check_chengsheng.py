import sqlite3, os

db = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
print('DB:', db)
print('Size:', os.path.getsize(db)/1024, 'KB')
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [t[0] for t in cur.fetchall()]
print('Tables:', tables)

if 'process_records' in tables:
    cur.execute('SELECT COUNT(*) FROM process_records')
    print('process_records count:', cur.fetchone()[0])
    cur.execute('SELECT id, order_no, product_name, status, quantity FROM process_records LIMIT 5')
    for r in cur.fetchall(): print('  ', r)

if 'production_orders' in tables:
    cur.execute('SELECT COUNT(*) FROM production_orders')
    print('production_orders count:', cur.fetchone()[0])
    cur.execute('SELECT * FROM production_orders LIMIT 3')
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall(): print('  ', dict(zip(cols, r)))

if 'orders' in tables:
    cur.execute('SELECT COUNT(*) FROM orders')
    print('orders count:', cur.fetchone()[0])
    cur.execute('SELECT * FROM orders LIMIT 3')
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall(): print('  ', dict(zip(cols, r)))

if 'workers' in tables:
    cur.execute('SELECT COUNT(*) FROM workers')
    print('workers count:', cur.fetchone()[0])
    cur.execute('SELECT * FROM workers LIMIT 3')
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall(): print('  ', dict(zip(cols, r)))

conn.close()
