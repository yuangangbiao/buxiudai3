import sqlite3
import os

os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

print("=" * 60)
print("深度检查数据库结构")
print("=" * 60)

# 1. 检查 container_center.db 表
print("\n[1] container_center.db 表结构")
try:
    conn = sqlite3.connect('mobile_api_ai/container_center.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"   表数量: {len(tables)}")
    for t in tables:
        print(f"   - {t[0]}")
        cursor.execute(f"PRAGMA table_info({t[0]})")
        cols = cursor.fetchall()
        print(f"     列: {[c[1] for c in cols]}")
    conn.close()
except Exception as e:
    print(f"   错误: {e}")

# 2. 检查数据库文件路径
print("\n[2] 数据库文件存在性检查")
db_files = [
    'mobile_api_ai/container_center.db',
    'container_center.db',
    'data.db'
]
for f in db_files:
    exists = os.path.exists(f)
    size = os.path.getsize(f) if exists else 0
    print(f"   {f}: {'存在' if exists else '不存在'} ({size} bytes)")

# 3. 检查队列表
print("\n[3] 队列表检查")
for db_name in ['mobile_api_ai/container_center.db']:
    if os.path.exists(db_name):
        try:
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [t[0] for t in cursor.fetchall()]
            for tbl in tables:
                if 'queue' in tbl.lower() or 'send' in tbl.lower() or 'dispatch' in tbl.lower():
                    print(f"   找到队列相关表: {tbl}")
                    cursor.execute(f"SELECT * FROM {tbl} LIMIT 5")
                    rows = cursor.fetchall()
                    print(f"   数据: {rows}")
            conn.close()
        except Exception as e:
            print(f"   {db_name}: {e}")

# 4. 检查进程状态
print("\n[4] 检查相关进程")
import subprocess
try:
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python*'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    py_procs = [l for l in lines if 'python' in l.lower() or 'pythonw' in l.lower()]
    print(f"   Python进程数: {len(py_procs)}")
    for p in py_procs[:10]:
        if p.strip():
            print(f"     {p}")
except Exception as e:
    print(f"   错误: {e}")

print("\n" + "=" * 60)
