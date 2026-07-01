import sqlite3
import os

os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

print("=" * 60)
print("对比两个数据库的 process_records")
print("=" * 60)

conn1 = sqlite3.connect('mobile_api_ai/wechat_container.db')
cursor1 = conn1.cursor()

conn2 = sqlite3.connect('mobile_api_ai/container_center.db')
cursor2 = conn2.cursor()

# wechat_container.db
print("\n[wechat_container.db] process_records:")
cursor1.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='process_records'")
if cursor1.fetchone():
    cursor1.execute('SELECT COUNT(*) FROM process_records')
    print(f"  记录数: {cursor1.fetchone()[0]}")
    cursor1.execute('SELECT id, order_no, status FROM process_records ORDER BY created_at DESC')
    for r in cursor1.fetchall():
        print(f"  {r}")
else:
    print("  process_records 表不存在")

# container_center.db
print("\n[container_center.db] process_records:")
cursor2.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='process_records'")
if cursor2.fetchone():
    cursor2.execute('SELECT COUNT(*) FROM process_records')
    print(f"  记录数: {cursor2.fetchone()[0]}")
else:
    print("  process_records 表不存在")

conn1.close()
conn2.close()

# 检查调度中心读取的是哪个数据库
print("\n" + "=" * 60)
print("检查调度中心的数据源")
print("=" * 60)

# 读取 dispatch_center.py 看看它用哪个数据库
with open('mobile_api_ai/dispatch_center.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找数据库路径相关代码
import re
db_patterns = re.findall(r'(container_center|wechat_container|dispatch_center_data)\.db', content)
print(f"\ndispatch_center.py 引用的数据库: {set(db_patterns)}")

# 检查缓存文件
cache_file = 'mobile_api_ai/dispatch_center_data.json'
if os.path.exists(cache_file):
    import json
    with open(cache_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"\ndispatch_center_data.json 记录数: {len(data)}")
    print("最新3条:")
    for item in data[-3:]:
        print(f"  {item.get('order_no', 'N/A')}, status={item.get('status', 'N/A')}")

print("\n" + "=" * 60)
