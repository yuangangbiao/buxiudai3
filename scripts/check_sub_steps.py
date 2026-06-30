import pymysql
conn = pymysql.connect(host='localhost', user='root', password='88888888', database='container_center', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
c = conn.cursor()
c.execute('SELECT id, order_no, step_name, process_code, quantity, operator, batch_no, status, created_at FROM process_sub_steps WHERE order_no=%s ORDER BY id DESC LIMIT 5', ('ORD-202604210002',))
rows = c.fetchall()
print('container_center.process_sub_steps 最新5条:')
for r in rows:
    bid = r.get('batch_no')
    print(f'  id={r["id"]} batch_no={bid} qty={r["quantity"]} op={r["operator"]} created_at={r["created_at"]}')
conn.close()

conn2 = pymysql.connect(host='localhost', user='root', password='88888888', database='steel_belt', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
c2 = conn2.cursor()
c2.execute('SELECT id, order_no, step_name, quantity, operator, batch_no, source, synced, created_at FROM process_sub_steps WHERE order_no=%s ORDER BY id DESC LIMIT 5', ('ORD-202604210002',))
rows2 = c2.fetchall()
print()
print('steel_belt.process_sub_steps 最新5条:')
for r in rows2:
    bid = r.get('batch_no')
    print(f'  id={r["id"]} batch_no={bid} qty={r["quantity"]} op={r["operator"]} source={r["source"]} synced={r["synced"]} created_at={r["created_at"]}')
conn2.close()
