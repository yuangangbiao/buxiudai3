import sqlite3

db = r'd:\yuan\backend\data\chengsheng.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

print('=== Check container_sync_records Table ===')

cols = cur.execute("PRAGMA table_info(container_sync_records)").fetchall()
print('Current columns:')
for c in cols:
    print(f'  {c[1]} ({c[2]})')

print('\n=== Check if customer_group exists ===')
col_names = [c[1] for c in cols]
if 'customer_group' not in col_names:
    print('Adding customer_group column...')
    cur.execute("ALTER TABLE container_sync_records ADD COLUMN customer_group TEXT DEFAULT ''")
    conn.commit()
    print('Done!')
else:
    print('customer_group already exists')

conn.close()
