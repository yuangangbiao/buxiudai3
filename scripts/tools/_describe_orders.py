"""查 container_center.orders 表结构"""
import pymysql
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='88888888', database='container_center', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()
cur.execute('DESCRIBE orders')
for r in cur.fetchall():
    print(f"  {r['Field']:30s} {r['Type']:30s} Null={r['Null']} Key={r['Key']} Default={r['Default']}")
print()
cur.execute("SELECT * FROM orders LIMIT 3")
for r in cur.fetchall(): print(' ', r)
conn.close()
