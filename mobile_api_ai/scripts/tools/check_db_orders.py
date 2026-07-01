import sqlite3, os

db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'chengsheng.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t['name'] for t in tables])

rows = conn.execute('SELECT order_id, name, material, spec FROM orders').fetchall()
print(f'Orders count: {len(rows)}')
for r in rows:
    d = dict(r)
    print(d)
    print(f'  material empty? {not (d["material"] or "").strip()}')
    print(f'  spec empty? {not (d["spec"] or "").strip()}')

conn.close()
