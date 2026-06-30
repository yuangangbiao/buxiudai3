import sqlite3, os, json

BASE = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'

def show_tables(db_path, label):
    if not os.path.exists(db_path):
        print(f'\n=== {label} ===')
        print('  [文件不存在]')
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f'\n=== {label} ===  {db_path}')
    for t in tables:
        cur2 = conn.cursor()
        cur2.execute(f'PRAGMA table_info([{t}])')
        cols = cur2.fetchall()
        print(f'\n  [{t}] ({len(cols)} 列)')
        for c in cols:
            print(f'    {c[1]:30s} {c[2]:20s}')
        cur2.execute(f'SELECT COUNT(*) FROM [{t}]')
        cnt = cur2.fetchone()[0]
        print(f'  -> 记录数: {cnt}')
    conn.close()

# 1. wechat_container.db
show_tables(os.path.join(BASE, 'wechat_container.db'), 'wechat_container.db')

# 2. chengsheng.db
show_tables(os.path.join(BASE, 'chengsheng.db'), 'chengsheng.db')

# 3. 检查 msg_db 目录下是否还有其他数据库文件
msg_db_dir = os.path.join(BASE, 'msg_db')
if os.path.exists(msg_db_dir):
    print(f'\n=== msg_db 目录 ===')
    for f in os.listdir(msg_db_dir):
        fpath = os.path.join(msg_db_dir, f)
        if f.endswith('.db'):
            show_tables(fpath, f'msg_db/{f}')
