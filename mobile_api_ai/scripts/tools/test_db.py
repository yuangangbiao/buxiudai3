import sqlite3, os
print("Python OK")
BASE = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai'
DB_CC = os.path.join(BASE, 'wechat_container.db')
DB_CS = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
print(f"Container DB exists: {os.path.exists(DB_CC)} ({os.path.getsize(DB_CC)} bytes)")
print(f"Chengsheng DB exists: {os.path.exists(DB_CS)} ({os.path.getsize(DB_CS)} bytes)")
conn = sqlite3.connect(DB_CC)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Container tables: {tables}")
conn.close()
print("Done")
