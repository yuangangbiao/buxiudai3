import sqlite3
import os

base = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
db_path = os.path.join(base, 'wechat_container.db')

print(f'DB path: {db_path}')
print(f'DB exists: {os.path.exists(db_path)}')
print(f'DB size: {os.path.getsize(db_path)} bytes')

conn = sqlite3.connect(db_path)
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [t[0] for t in cursor.fetchall()]
print(f'Tables: {tables}')

if 'process_sub_steps' in tables:
    cursor = conn.execute("SELECT COUNT(*) FROM process_sub_steps")
    count = cursor.fetchone()[0]
    print(f'process_sub_steps count: {count}')
    
    cursor = conn.execute("SELECT DISTINCT order_no FROM process_sub_steps")
    orders = [r[0] for r in cursor.fetchall()]
    print(f'Distinct order_no in process_sub_steps: {orders}')
    
    cursor = conn.execute("SELECT * FROM process_sub_steps ORDER BY created_at DESC LIMIT 10")
    rows = cursor.fetchall()
    col_names = [d[0] for d in cursor.description]
    print(f'Columns: {col_names}')
    for row in rows:
        print(row)
    
    # Search for wo2026050009
    cursor = conn.execute("SELECT * FROM process_sub_steps WHERE order_no LIKE ?", ('%wo2026050009%',))
    found = cursor.fetchall()
    print(f'Matching wo2026050009: {len(found)} records')

if 'process_records' in tables:
    cursor = conn.execute("SELECT id, order_no, order_no FROM process_records WHERE order_no LIKE ? OR order_no LIKE ?", ('%wo2026050009%', '%wo2026050009%'))
    found = cursor.fetchall()
    print(f'process_records matching wo2026050009: {len(found)} records')
    for row in found:
        print(row)
    
    cursor = conn.execute("SELECT id, order_no, order_no FROM process_records ORDER BY updated_at DESC LIMIT 10")
    rows = cursor.fetchall()
    print('Recent process_records:')
    for row in rows:
        print(row)

conn.close()
