"""Verify synced data in chengsheng.db"""
import sqlite3

DB_CS = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
conn = sqlite3.connect(DB_CS)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. Orders
print('=' * 50)
print('ORDERS TABLE')
print('=' * 50)
cur.execute('SELECT order_id, name, status, priority, delivery_date FROM orders')
for r in cur.fetchall():
    print('  %s | %s | %s | %s | %s' % (
        r['order_id'], r['name'], r['status'], r['priority'], r['delivery_date']))

# 2. Workers
print('\n' + '=' * 50)
print('WORKERS TABLE')
print('=' * 50)
cur.execute('SELECT id, username, name, role, source FROM workers')
for r in cur.fetchall():
    print('  %s | %s | %s | %s | %s' % (r['id'], r['username'], r['name'], r['role'], r['source']))

# 3. Order Processes
print('\n' + '=' * 50)
print('ORDER PROCESSES TABLE')
print('=' * 50)
cur.execute('SELECT order_id, process_key, sequence FROM order_processes ORDER BY order_id, sequence')
for r in cur.fetchall():
    print('  %s | [%d] %s' % (r['order_id'], r['sequence'], r['process_key']))

# 4. Sub Steps
print('\n' + '=' * 50)
print('SUB STEPS TABLE')
print('=' * 50)
cur.execute('SELECT step_id, order_no, step_name, quantity, operator, remark FROM sub_steps')
for r in cur.fetchall():
    print('  %s | %s | %.1f件 | 操作人:%s | 备注:%s' % (
        r['order_no'], r['step_name'], r['quantity'], r['operator'], r['remark']))

# 5. Container Sync Records
print('\n' + '=' * 50)
print('CONTAINER SYNC RECORDS TABLE')
print('=' * 50)
cur.execute('SELECT order_no, product_name, quantity, unit, customer_name, status FROM container_sync_records')
for r in cur.fetchall():
    print('  %s | %s | %s%s | 客户:%s | %s' % (
        r['order_no'], r['product_name'], r['quantity'], r['unit'],
        r['customer_name'], r['status']))

conn.close()
