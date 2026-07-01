import os, sqlite3, re
parent = os.path.dirname(os.path.abspath(__file__))
db = os.environ.get('CHENGSHENG_DB_PATH', os.path.join(parent, 'chengsheng.db'))
c = sqlite3.connect(db).cursor()
for tbl in ['orders','workers','sub_steps','attendance','production_orders','process_records','order_processes']:
    try:
        c.execute(f'PRAGMA table_info({tbl})')
        cols = c.fetchall()
        if not cols: continue
        print(f'\n=== {tbl} ===')
        print(f'  columns: {[(r[1],r[2],"PK" if r[5] else "") for r in cols]}')
        c.execute(f'SELECT COUNT(*) FROM {tbl}')
        print(f'  count: {c.fetchone()[0]}')
        c.execute(f'SELECT * FROM {tbl} LIMIT 2')
        col_names = [r[1] for r in cols]
        for row in c.fetchall():
            print(f'  {dict(zip(col_names,row))}')
    except Exception as e:
        print(f'\n=== {tbl} === error: {e}')
c.close()
