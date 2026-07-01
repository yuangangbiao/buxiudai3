import sqlite3
import os

db_paths = [
    'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db',
]

for db_path in db_paths:
    if os.path.exists(db_path):
        print('=== DB: %s ===' % db_path)
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cur.fetchall()
        print('Tables:')
        for t in tables:
            cur.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name="%s"' % t[0])
            row = cur.fetchone()
            if row:
                print('  %s' % row[0].replace('\n','\n    '))
        # Sample data from key tables
        for tbl in ['orders', 'sub_steps', 'order_processes']:
            try:
                cur.execute('SELECT * FROM %s' % tbl)
                rows = cur.fetchall()
                print('\n=== %s rows: %d ===' % (tbl, len(rows)))
                for r in rows:
                    print('  %s' % str(r))
                if rows:
                    print('  Columns: %s' % str([d[0] for d in cur.description]))
            except Exception as e:
                print('\n=== %s: %s ===' % (tbl, e))
        conn.close()
    else:
        print('=== NOT FOUND: %s ===' % db_path)
