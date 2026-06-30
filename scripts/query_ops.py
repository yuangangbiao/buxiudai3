import sqlite3

for db in ['data/hr.db', 'data/steel_belt.db']:
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f'{db}: {tables}')

        if 'operators' in tables:
            cur.execute('SELECT id, name, role FROM operators LIMIT 10')
            for row in cur.fetchall():
                print(f'  operator: {row}')
        conn.close()
    except Exception as e:
        print(f'{db}: ERROR {e}')
