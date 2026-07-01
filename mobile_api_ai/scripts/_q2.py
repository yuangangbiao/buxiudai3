import sqlite3
DB = 'D:/yuan/不锈钢网带跟单3.0/mobile_api_ai/wechat_container.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()
print("=== process_records ===")
cur.execute('SELECT id,order_no,work_order_no,product_name,quantity,status FROM process_records LIMIT 20')
for r in cur.fetchall():
    print('|'.join([str(x) if x else '' for x in r[:6]]))
print("=== process_sub_steps ===")
cur.execute('SELECT id,process_id,order_no,step_name,quantity,operator FROM process_sub_steps LIMIT 20')
for r in cur.fetchall():
    print('|'.join([str(x) if x else '' for x in r[:6]]))
conn.close()
