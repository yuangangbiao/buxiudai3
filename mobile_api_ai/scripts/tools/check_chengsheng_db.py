import sqlite3, os
os.chdir(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
conn = sqlite3.connect('chengsheng.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = c.fetchall()
print('=== chengsheng.db 表列表 ===')
for t in tables:
    c.execute('PRAGMA table_info("%s")' % t[0])
    cols = c.fetchall()
    col_names = [col[1] for col in cols]
    print(f'\n  {t[0]}  ({len(cols)} 列)')
    print(f'    列: {", ".join(col_names)}')
conn.close()
