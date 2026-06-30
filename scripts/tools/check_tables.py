import sqlite3, os
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'steel_belt.db')
print(f'DB exists: {os.path.exists(db_path)}')
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [t[0] for t in c.fetchall()]
print(f'Tables: {tables}')
conn.close()
print('DONE')
