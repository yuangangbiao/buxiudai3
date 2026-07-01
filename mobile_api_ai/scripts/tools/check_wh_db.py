import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'wechat_container.db')
print(f"DB路径: {DB}")

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [t[0] for t in cur.fetchall()]
print(f"表: {tables}")

for tn in tables:
    cur.execute(f"SELECT COUNT(*) FROM [{tn}]")
    cnt = cur.fetchone()[0]
    cur.execute(f"PRAGMA table_info([{tn}])")
    cols = [c[1] for c in cur.fetchall()]
    has_awaiting = any('awaiting' in c.lower() or 'warehous' in c.lower() or 'process' in c.lower() for c in cols)
    if cnt > 0 and ('process' in tn.lower() or 'schedule' in tn.lower() or 'order' in tn.lower() or has_awaiting):
        print(f"\n--- {tn} ({cnt}行) ---")
        print(f"列: {cols}")
        cur.execute(f"SELECT * FROM [{tn}] LIMIT 5")
        for row in cur.fetchall():
            r = dict(zip(cols, row))
            print(f"  {r}")

conn.close()
