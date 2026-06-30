# -*- coding: utf-8 -*-
"""检查所有可能的容器中心数据库"""
import sqlite3, os

base = os.path.join(os.path.dirname(__file__), '..', '..', 'mobile_api_ai')
base = os.path.normpath(base)

dbs = [
    os.path.join(base, 'wechat_container.db'),
    os.path.join(base, 'container_center.db'),
    os.path.join(base, '..', 'wechat_container.db'),
    os.path.join(base, '..', 'container_center.db'),
]

for db_path in dbs:
    db_path = os.path.normpath(db_path)
    if not os.path.exists(db_path):
        print(f'[不存在] {db_path}')
        continue
    size = os.path.getsize(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    
    has_pr = 'process_records' in tables
    has_sr = 'schedule_records' in tables
    
    print(f'\n[存在] {db_path} ({size} bytes)')
    print(f'  表({len(tables)}): {", ".join(tables[:15])}{"..." if len(tables)>15 else ""}')
    print(f'  有 process_records: {has_pr}')
    print(f'  有 schedule_records: {has_sr}')
    
    if has_pr:
        cur.execute('SELECT COUNT(*) FROM process_records')
        print(f'  process_records 记录数: {cur.fetchone()[0]}')
        cur.execute('PRAGMA table_info(process_records)')
        cols = [(c[1], c[2]) for c in cur.fetchall()]
        cur.execute('SELECT * FROM process_records')
        rows = cur.fetchall()
        for r in rows[:5]:
            d = dict(zip([c[0] for c in cols], r))
            print(f'    id={d["id"]} work_order_no={d.get("work_order_no")} order_no={d.get("order_no")}')
    
    if has_sr:
        cur.execute('SELECT COUNT(*) FROM schedule_records')
        print(f'  schedule_records 记录数: {cur.fetchone()[0]}')
        cur.execute('PRAGMA table_info(schedule_records)')
        cols = [(c[1], c[2]) for c in cur.fetchall()]
        cur.execute('SELECT * FROM schedule_records')
        rows = cur.fetchall()
        for r in rows[:5]:
            d = dict(zip([c[0] for c in cols], r))
            print(f'    id={d["id"]} work_order_no={d.get("work_order_no")}')
    
    conn.close()
