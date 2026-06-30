import pymysql

conn = pymysql.connect(host='localhost', user='root', password='88888888', database='container_center', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()

c.execute(
    'SELECT id, order_no, step_name, process_code, quantity, operator, batch_no, status, created_at '
    'FROM process_sub_steps WHERE order_no=%s AND created_at > %s ORDER BY id DESC LIMIT 10',
    ('ORD-202604210002', '2026-06-20'))
rows = c.fetchall()
print(f'container_center 今天 ORD-202604210002 的记录: {len(rows)} 条')
for r in rows:
    bid = r.get('batch_no')
    print(f'  id={r["id"]} batch_no={bid} qty={r["quantity"]} op={r["operator"]} status={r["status"]} created_at={r["created_at"]}')

c.execute('SHOW COLUMNS FROM process_sub_steps LIKE "batch_no"')
col = c.fetchone()
print(f'\nbatch_no 列存在: {col is not None}')
if col:
    print(f'  字段: {col}')

c.execute('SELECT COUNT(*) as cnt FROM process_sub_steps WHERE batch_no IS NOT NULL AND batch_no != ""')
row = c.fetchone()
print(f'有 batch_no 值的记录数: {row["cnt"]}')

conn.close()
