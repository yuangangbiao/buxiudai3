import pymysql
import sys

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='88888888', database='container_center', charset='utf8mb4')
cur = conn.cursor()
cur.execute('SELECT id, order_no, material, spec FROM production_orders LIMIT 5')
rows = cur.fetchall()
print('=== production_orders (material/spec) ===')
for r in rows:
    print(r)
conn.close()
