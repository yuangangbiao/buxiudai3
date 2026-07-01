import sqlite3
db_path = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print('=== 表列表 ===')
for t in tables:
    print(f'\n  {t[0]}')
    cursor.execute(f'PRAGMA table_info({t[0]})')
    cols = cursor.fetchall()
    for c in cols:
        nullable = 'NOT NULL' if c[3] else 'NULL'
        dflt = f'  default={c[4]}' if c[4] else ''
        print(f'    ├─ {c[1]}  ({c[2]})  {nullable}{dflt}')
conn.close()
