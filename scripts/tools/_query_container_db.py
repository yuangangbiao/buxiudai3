import sqlite3

db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('=== 表列表 ===')
for t in tables:
    print(f'  {t[0]}')

# data_packages 表结构
cur.execute('PRAGMA table_info(data_packages)')
cols = cur.fetchall()
print('\n=== data_packages 表结构 ===')
for c in cols:
    print(f'  {c[1]} ({c[2]})')

# work_order 类型
cur.execute("SELECT id, data_type, status, related_order, created_at FROM data_packages WHERE data_type='work_order' ORDER BY created_at DESC LIMIT 20")
rows = cur.fetchall()
print(f'\n=== work_order 记录 ({len(rows)}条) ===')
for r in rows:
    print(f'  id={r[0]}, type={r[1]}, status={r[2]}, order={r[3]}, time={r[4]}')

# report/process 类型
cur.execute("SELECT id, data_type, status, related_order, created_at FROM data_packages WHERE data_type IN ('report', 'process') ORDER BY created_at DESC LIMIT 20")
rows = cur.fetchall()
print(f'\n=== report/process 记录 ({len(rows)}条) ===')
for r in rows:
    print(f'  id={r[0]}, type={r[1]}, status={r[2]}, order={r[3]}, time={r[4]}')

# 所有 data_type 分布
cur.execute('SELECT DISTINCT data_type FROM data_packages ORDER BY data_type')
types = cur.fetchall()
print(f'\n=== 所有 data_type 类型分布 ===')
for t in types:
    cur.execute('SELECT COUNT(*) FROM data_packages WHERE data_type=?', (t[0],))
    cnt = cur.fetchone()[0]
    print(f'  {t[0]}: {cnt}条')

# doc_data 包含 process/report 关键词
cur.execute("SELECT id, data_type, related_order, length(doc_data) as data_len FROM data_packages WHERE doc_data LIKE '%process%' OR doc_data LIKE '%report%' LIMIT 5")
rows = cur.fetchall()
print(f'\n=== doc_data 包含 process/report ({len(rows)}条) ===')
for r in rows:
    print(f'  id={r[0]}, type={r[1]}, order={r[2]}, data_len={r[3]}')

conn.close()
