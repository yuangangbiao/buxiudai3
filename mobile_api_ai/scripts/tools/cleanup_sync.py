import sqlite3

DB_CS = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
conn = sqlite3.connect(DB_CS)
cur = conn.cursor()

# 清除所有已同步的数据，准备重新同步
cur.execute("DELETE FROM orders")
cur.execute("DELETE FROM container_sync_records")
cur.execute("DELETE FROM order_processes")
cur.execute("DELETE FROM sub_steps")
cur.execute("DELETE FROM workers WHERE source='container_sync'")
conn.commit()

print('=== Cleanup complete ===')
for t in ['orders', 'container_sync_records', 'order_processes', 'sub_steps', 'workers']:
    cur.execute('SELECT COUNT(*) FROM "%s"' % t)
    print('%s: %d rows' % (t, cur.fetchone()[0]))
conn.close()
