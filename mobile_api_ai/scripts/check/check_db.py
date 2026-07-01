import sqlite3
import os

_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
db_path = os.path.join(_project_root, 'wechat_container.db')

if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM data_packages')
    total = cur.fetchone()[0]
    print(f"总记录数: {total}")

    cur.execute('SELECT COUNT(*) FROM data_packages WHERE status != "completed"')
    pending = cur.fetchone()[0]
    print(f"未完成任务: {pending}")

    cur.execute('SELECT COUNT(*) FROM data_packages WHERE status = "pending"')
    waiting = cur.fetchone()[0]
    print(f"待处理任务: {waiting}")

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print(f"\n数据库表: {[t[0] for t in tables]}")

    conn.close()