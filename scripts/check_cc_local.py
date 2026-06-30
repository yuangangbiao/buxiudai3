import pymysql

# 检查 container_center_local（5008 写入的数据库）
conn = pymysql.connect(host='localhost', user='root', password='88888888', database='container_center_local', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()

# process_sub_steps 表是否存在
c.execute("SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_schema='container_center_local' AND table_name='process_sub_steps'")
row = c.fetchone()
print(f'container_center_local process_sub_steps 表存在: {row["cnt"] > 0}')

if row['cnt'] > 0:
    c.execute('SELECT id, order_no, step_name, process_code, quantity, operator, batch_no, status, created_at FROM process_sub_steps WHERE order_no=%s ORDER BY id DESC LIMIT 5', ('ORD-202604210002',))
    rows = c.fetchall()
    print(f'找到 {len(rows)} 条 ORD-202604210002 记录:')
    for r in rows:
        print(f'  id={r["id"]} batch_no={r.get("batch_no")} qty={r["quantity"]} op={r["operator"]} status={r["status"]} created_at={r["created_at"]}')
else:
    print('表不存在')

conn.close()

# 也检查 container_center 看看是否有使用 batch_no 的最新记录
conn2 = pymysql.connect(host='localhost', user='root', password='88888888', database='container_center', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
c2 = conn2.cursor()
c2.execute("SHOW CREATE TABLE process_sub_steps")
ddl = c2.fetchone()
print(f'\ncontainer_center.process_sub_steps DDL:')
print(ddl['Create Table'] if ddl else '表不存在')
conn2.close()
