"""测试 SQL"""
import pymysql
from datetime import datetime
conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='88888888', database='steel_belt', connect_timeout=5, cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()
try:
    cur.execute("SELECT * FROM orders WHERE updated_at >= %s ORDER BY updated_at ASC LIMIT 1", (datetime(1900, 1, 1),))
    print("OK with datetime:", cur.fetchone() is not None)
except Exception as e:
    print("FAIL datetime:", e)
try:
    cur.execute("SELECT * FROM orders WHERE updated_at >= %s ORDER BY updated_at ASC LIMIT 1", ('1900-01-01 00:00:00',))
    print("OK with str:", cur.fetchone() is not None)
except Exception as e:
    print("FAIL str:", e)
try:
    cur.execute("SELECT * FROM orders WHERE updated_at >= '1900-01-01 00:00:00' ORDER BY updated_at ASC LIMIT 1")
    print("OK with literal:", cur.fetchone() is not None)
except Exception as e:
    print("FAIL literal:", e)
conn.close()
