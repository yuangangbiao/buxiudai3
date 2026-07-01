import sqlite3, os

db = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Check orders table
cur.execute("PRAGMA table_info(orders)")
cols = cur.fetchall()
print('orders columns:', [(c[1], c[2]) for c in cols])
cur.execute('SELECT COUNT(*) FROM orders')
print('orders count:', cur.fetchone()[0])
cur.execute('SELECT * FROM orders LIMIT 5')
for r in cur.fetchall():
    print('  ', dict(zip([c[1] for c in cols], r)))

# Check production_orders table
cur.execute("PRAGMA table_info(production_orders)")
cols = cur.fetchall()
print('\nproduction_orders columns:', [(c[1], c[2]) for c in cols])
cur.execute('SELECT COUNT(*) FROM production_orders')
print('production_orders count:', cur.fetchone()[0])
cur.execute('SELECT * FROM production_orders LIMIT 5')
for r in cur.fetchall():
    print('  ', dict(zip([c[1] for c in cols], r)))

# Check process_records columns
cur.execute("PRAGMA table_info(process_records)")
cols = cur.fetchall()
print('\nprocess_records columns:', [(c[1], c[2]) for c in cols])

# Check workers
cur.execute("PRAGMA table_info(workers)")
cols = cur.fetchall()
print('\nworkers columns:', [(c[1], c[2]) for c in cols])
cur.execute('SELECT COUNT(*) FROM workers')
print('workers count:', cur.fetchone()[0])
cur.execute('SELECT * FROM workers LIMIT 5')
for r in cur.fetchall():
    print('  ', dict(zip([c[1] for c in cols], r)))

# Check sub_steps
cur.execute("PRAGMA table_info(sub_steps)")
cols = cur.fetchall()
if cols:
    print('\nsub_steps columns:', [(c[1], c[2]) for c in cols])
    cur.execute('SELECT COUNT(*) FROM sub_steps')
    print('sub_steps count:', cur.fetchone()[0])
    cur.execute('SELECT * FROM sub_steps LIMIT 3')
    for r in cur.fetchall():
        print('  ', dict(zip([c[1] for c in cols], r)))

# Check order_processes
cur.execute("PRAGMA table_info(order_processes)")
cols = cur.fetchall()
if cols:
    print('\norder_processes columns:', [(c[1], c[2]) for c in cols])
    cur.execute('SELECT COUNT(*) FROM order_processes')
    print('order_processes count:', cur.fetchone()[0])
    cur.execute('SELECT * FROM order_processes LIMIT 3')
    for r in cur.fetchall():
        print('  ', dict(zip([c[1] for c in cols], r)))

conn.close()
