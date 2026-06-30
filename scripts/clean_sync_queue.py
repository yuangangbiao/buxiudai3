import pymysql

conn = pymysql.connect(host='localhost', user='root', password='88888888', database='steel_belt', charset='utf8mb4')
c = conn.cursor()

c.execute("SELECT id, order_no, step_name, operator, quantity, status, enqueued_at FROM sync_queue WHERE order_no='ORD-202604210002' AND step_name='编制右旋' AND operator='苑岗彪'")
rows = c.fetchall()
print(f'找到 {len(rows)} 条相关记录:')
for r in rows:
    print(f'  id={r[0]} status={r[5]} enqueued_at={r[6]}')

c.execute("DELETE FROM sync_queue WHERE order_no='ORD-202604210002' AND step_name='编制右旋' AND operator='苑岗彪'")
print(f'已删除 {c.rowcount} 条')
conn.commit()
conn.close()
