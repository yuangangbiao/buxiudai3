"""查 container_center.orders 状态和索引"""
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='88888888', database='container_center', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) c FROM orders')
print('container_center.orders total:', cur.fetchone()['c'])
cur.execute("SHOW INDEX FROM orders")
for r in cur.fetchall():
    print(' idx:', r['Key_name'], 'col:', r['Column_name'], 'unique:', not r['Non_unique'])
print()
cur.execute("SELECT order_no FROM orders ORDER BY id ASC LIMIT 15")
print("--- 前 15 条 order_no ---")
for r in cur.fetchall(): print(' ', r['order_no'])
conn.close()
