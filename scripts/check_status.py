import sys, os
os.environ["INVENTORY_API_KEY"] = "dev-check"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute('SELECT DISTINCT status FROM orders')
print('orders表 status 所有值:', [r['status'] for r in cursor.fetchall()])

cursor.execute('SELECT DISTINCT po.status FROM production_orders po')
print('production_orders表 status 所有值:', [r['status'] for r in cursor.fetchall()])

cursor.execute('SELECT id, order_no, status, is_deleted, created_at FROM orders ORDER BY id')
print('\norders表 全量:')
for r in cursor.fetchall():
    print(f'  id={r["id"]}, order_no={r["order_no"]}, status={r["status"]}, is_deleted={r["is_deleted"]}, created_at={r["created_at"]}')

cursor.close()
conn.close()
