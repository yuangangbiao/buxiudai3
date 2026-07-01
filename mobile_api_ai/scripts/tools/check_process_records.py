import sqlite3
import os

os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

conn = sqlite3.connect('mobile_api_ai/container_center.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print('process_records' in tables)
print('可用表:', tables)

# 尝试查询 process_records 表
try:
    cursor.execute('SELECT COUNT(*) FROM process_records')
    count = cursor.fetchone()[0]
    print(f'process_records 记录数: {count}')
except Exception as e:
    print(f'process_records 表错误: {e}')

conn.close()
