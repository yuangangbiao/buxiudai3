# -*- coding: utf-8 -*-
"""检查容器中心 SQLite 数据库"""
import sqlite3, os

db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'mobile_api_ai', 'container_center.db')
db_path = os.path.normpath(db_path)
print(f'DB: {db_path}')

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print(f'Tables ({len(tables)}): {tables}')

if 'process_records' in tables:
    cur.execute('PRAGMA table_info(process_records)')
    cols = [(c[1], c[2]) for c in cur.fetchall()]
    print(f'\nprocess_records columns: {cols}')
    cur.execute('SELECT * FROM process_records')
    rows = cur.fetchall()
    print(f'Total records: {len(rows)}')
    for r in rows:
        d = dict(zip([c[0] for c in cols], r))
        print(f'  id={d.get("id")} work_order_no={d.get("work_order_no")} order_no={d.get("order_no")} status={d.get("status")}')
else:
    print('\nprocess_records table NOT FOUND')

    # Check all tables for the record
    for tname in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{tname}"')
        cnt = cur.fetchone()[0]
        if cnt > 0:
            cur.execute(f'PRAGMA table_info("{tname}")')
            cols = [c[1] for c in cur.fetchall()]
            print(f'  {tname}: {cnt} rows, cols={cols}')

conn.close()
