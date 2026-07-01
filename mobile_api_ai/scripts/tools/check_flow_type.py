import sqlite3
import os
os.chdir(r"d:\yuan\不锈钢网带跟单3.0")
conn = sqlite3.connect('mobile_api_ai/wechat_container.db')
cursor = conn.cursor()

# 检查 process_records 表列
cursor.execute("PRAGMA table_info(process_records)")
cols = cursor.fetchall()
print("process_records 表列:")
for c in cols:
    print(f"  {c[1]} ({c[2]})")

# 检查最近记录的 flow_type
cursor.execute("SELECT id, order_no, order_no, flow_type, status FROM process_records ORDER BY created_at DESC LIMIT 5")
print("\n最近记录:")
for r in cursor.fetchall():
    print(f"  {r}")

conn.close()
