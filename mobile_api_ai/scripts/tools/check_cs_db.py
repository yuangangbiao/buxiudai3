"""检查 chengsheng.db 状态"""
import sqlite3
import os

parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
cs_path = os.environ.get('CHENGSHENG_DB_PATH', os.path.join(parent, 'chengsheng.db'))
paths = [os.path.abspath(cs_path)]

for p in set(paths):
    real = os.path.normpath(p)
    print(f'路径: {real}')
    print(f'  存在: {os.path.exists(real)}')
    if os.path.exists(real):
        conn = sqlite3.connect(real)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        print(f'  表: {tables}')
        if 'sub_steps' in tables:
            cur.execute('SELECT COUNT(*) as cnt FROM sub_steps')
            cnt = cur.fetchone()['cnt']
            print(f'  sub_steps 记录数: {cnt}')
            if cnt > 0:
                cur.execute('SELECT * FROM sub_steps ORDER BY created_at DESC LIMIT 5')
                for r in cur.fetchall():
                    print(f'    id={r["id"][:8]}... order_no={r["order_no"]} step={r["step_name"]} qty={r["quantity"]}')
        else:
            print('  缺少 sub_steps 表')
        conn.close()
