import pymysql

conn = pymysql.connect(host='localhost', user='root', password='88888888', database='steel_belt', charset='utf8mb4')
c = conn.cursor()

c.execute("SELECT id, order_no, step_name, operator, quantity, status, enqueued_at FROM sync_queue WHERE status IN ('pending','retry')")
rows = c.fetchall()
print(f'pending/retry 记录数: {len(rows)}')
for r in rows:
    print(r)

c.execute("SHOW INDEX FROM sync_queue WHERE Non_unique=0")
print('\n唯一索引:')
for r in c.fetchall():
    print(f'  {r[2]} on {r[4]}')

c.execute("DESCRIBE sync_queue")
print('\nsync_queue 表结构:')
for r in c.fetchall():
    print(f'  {r[0]:20s} {r[1]:15s} nullable={r[2]} key={r[3]}')

conn.close()
