"""检查 steel_belt.db 中 sub_steps 表的 overtime 字段状态"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'steel_belt.db')
db_path = os.path.normpath(db_path)

if not os.path.exists(db_path):
    print(f'[ERROR] 数据库不存在: {db_path}')
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print(f'=== 数据库: {db_path}')
print(f'=== 表数量: {len(tables)}')

if 'sub_steps' in tables:
    cur.execute('PRAGMA table_info(sub_steps)')
    cols = cur.fetchall()
    print('\n=== sub_steps 列定义 ===')
    for c in cols:
        overtime_flag = ' <<<< overtime字段' if 'overtime' in c[1] else ''
        print(f'  {c[0]}: {c[1]} ({c[2]})  null={c[3]}  default={c[4]}{overtime_flag}')

    cur.execute('SELECT COUNT(*) FROM sub_steps')
    count = cur.fetchone()[0]
    print(f'\n=== sub_steps 总记录数: {count}')

    if count > 0:
        cur.execute('SELECT overtime_hours, overtime_minutes FROM sub_steps LIMIT 5')
        rows = cur.fetchall()
        print('=== 前5条 overtime 数据 ===')
        for row in rows:
            print(f'  overtime_hours={row[0]}, overtime_minutes={row[1]}')
else:
    print('\n[INFO] sub_steps 表不存在，无需迁移')

conn.close()
