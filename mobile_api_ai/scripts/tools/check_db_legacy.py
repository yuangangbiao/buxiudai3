import sqlite3, os
db = os.path.join(r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai', 'wechat_container.db')
print('DB exists:', os.path.exists(db))
print('DB size:', os.path.getsize(db), 'bytes')
conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cur.fetchall()
print('Tables:', [t[0] for t in tables])
if ('process_records',) in tables:
    cur.execute('SELECT COUNT(*) FROM process_records')
    cnt = cur.fetchone()[0]
    print('process_records count:', cnt)
    cur.execute('SELECT id, order_no, product_name, status, quantity, created_at FROM process_records LIMIT 5')
    for row in cur.fetchall():
        print('  ', row)
else:
    print('process_records table NOT FOUND')
conn.close()
