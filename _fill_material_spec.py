import pymysql

data = [
    ('ORD-202604210001', '304',  ''),
    ('ORD-202604210002', '304',  ''),
    ('ORD-202604210004', '304',  ''),
    ('ORD-202605010001', '304',  ''),
    ('ORD-202605020001', '304不锈钢', ''),
]

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root',
                        password='88888888', database='container_center', charset='utf8mb4')
cur = conn.cursor()

print('=== 写入 production_orders.material/spec ===')
for order_no, material, spec in data:
    cur.execute(
        "UPDATE production_orders SET material=%s, spec=%s WHERE order_no=%s",
        (material, spec, order_no))
    affected = cur.rowcount
    print(f'  {order_no}: material={material}, spec={spec!r} → {affected} 行更新')

conn.commit()

cur.execute("SELECT id, order_no, material, spec FROM production_orders ORDER BY id")
rows = cur.fetchall()
print(f'\n=== 验证 ({len(rows)} 条) ===')
for r in rows:
    print(f'  id={r[0]}, order={r[1]}, material={r[2]}, spec={r[3]}')

conn.close()
print('\n[OK] 完成')
