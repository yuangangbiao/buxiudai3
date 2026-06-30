"""检查所有 SQLite 数据库中 sub_steps 表的状态"""
import sqlite3
import os
import glob

data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
data_dir = os.path.normpath(data_dir)

db_files = glob.glob(os.path.join(data_dir, '*.db'))

for db_path in sorted(db_files):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    
    if not tables:
        conn.close()
        continue
    
    db_name = os.path.basename(db_path)
    
    if 'sub_steps' in tables:
        print(f'\n=== {db_name} === (表数: {len(tables)})')
        cur.execute('PRAGMA table_info(sub_steps)')
        cols = cur.fetchall()
        for c in cols:
            flag = ' <<<< overtime字段' if 'overtime' in c[1] else ''
            print(f'  {c[0]}: {c[1]} ({c[2]})  null={c[3]}  default={c[4]}{flag}')
        
        cur.execute('SELECT COUNT(*) FROM sub_steps')
        count = cur.fetchone()[0]
        print(f'  >> 记录数: {count}')
    else:
        print(f'  {db_name}: {len(tables)} 张表, 无 sub_steps')
    
    conn.close()
