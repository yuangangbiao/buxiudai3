import os
import sqlite3

parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.environ.get('CHENGSHENG_DB_PATH', os.path.join(parent, 'chengsheng.db'))
conn = sqlite3.connect(db_path)
cur = conn.cursor()

for tbl in ['orders', 'workers', 'sub_steps', 'attendance', 'production_orders', 'process_records', 'order_processes']:
    try:
        cur.execute('PRAGMA table_info(%s)' % tbl)
        cols = cur.fetchall()
        if cols:
            print('\n=== %s ===' % tbl)
            print('columns:', [(c[1], c[2], 'PK' if c[5] else '') for c in cols])
            cur.execute('SELECT COUNT(*) FROM %s' % tbl)
            print('count:', cur.fetchone()[0])
            cur.execute('SELECT * FROM %s LIMIT 3' % tbl)
            for r in cur.fetchall():
                print('  ', dict(zip([c[1] for c in cols], r)))
        else:
            print('\n=== %s === (no columns)' % tbl)
    except Exception as e:
        print('\n=== %s === error: %s' % (tbl, e))
conn.close()
