import sqlite3, os

mobile_api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(mobile_api_dir)

print('=== wechat_container.db (绝对路径) ===')
db_path = os.path.join(mobile_api_dir, 'wechat_container.db')
print(f'路径: {db_path}')
print(f'存在: {os.path.exists(db_path)}')
if os.path.exists(db_path):
    print(f'大小: {os.path.getsize(db_path)} bytes')

print()
print('=== wechat_container.db (相对路径) ===')
rel_path = 'wechat_container.db'
print(f'路径: {os.path.abspath(rel_path)}')
print(f'存在: {os.path.exists(rel_path)}')
if os.path.exists(rel_path):
    print(f'大小: {os.path.getsize(rel_path)} bytes')

if os.path.exists(db_path):
    print()
    print('=== 数据库表列表 ===')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    for t in tables:
        print(f'  表: {t[0]}')
    
    print()
    print('=== process_sub_steps 表结构 ===')
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='process_sub_steps'")
    row = cursor.fetchone()
    if row:
        print(row[0])
        cursor.execute("SELECT COUNT(*) FROM process_sub_steps")
        count = cursor.fetchone()[0]
        print(f'记录数: {count}')
        if count > 0:
            cursor.execute("SELECT * FROM process_sub_steps ORDER BY created_at DESC LIMIT 5")
            rows = cursor.fetchall()
            for r in rows:
                print(dict(r))
    else:
        print('表 process_sub_steps 不存在!')
    
    print()
    print('=== process_records 表结构 ===')
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='process_records'")
    row = cursor.fetchone()
    if row:
        print('存在')
        cursor.execute("SELECT COUNT(*) FROM process_records")
        count = cursor.fetchone()[0]
        print(f'记录数: {count}')
        if count > 0:
            cursor.execute("SELECT id, order_no, quantity FROM process_records ORDER BY created_at DESC LIMIT 5")
            for r in cursor.fetchall():
                print(dict(r))
    else:
        print('表 process_records 不存在!')
    
    conn.close()
