import sqlite3
db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("DELETE FROM process_records WHERE order_no='WO-IDEM-003'")
conn.commit()
print('deleted:', c.rowcount)
c.execute('SELECT COUNT(*) FROM process_records')
print('total:', c.fetchone()[0])
conn.close()
