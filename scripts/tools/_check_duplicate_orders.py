"""查 orders 重复数据"""
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='88888888', database='steel_belt', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()
cur.execute("SELECT order_no, COUNT(*) c FROM orders GROUP BY order_no HAVING c > 1 ORDER BY c DESC LIMIT 10")
print("=== steel_belt.orders 重复 order_no ===")
for r in cur.fetchall():
    print(f"  {r['order_no']:35s} count={r['c']}")
print()
cur.execute("SELECT COUNT(*) total FROM orders")
print(f"total orders: {cur.fetchone()['total']}")
cur.execute("SELECT COUNT(DISTINCT order_no) distinct_count FROM orders")
print(f"distinct order_no: {cur.fetchone()['distinct_count']}")
conn.close()
