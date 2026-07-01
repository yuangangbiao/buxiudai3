import sqlite3
import os

os.chdir(r"d:\yuan\不锈钢网带跟单3.0")

print("=" * 60)
print("检查数据库文件")
print("=" * 60)

db_files = [
    'mobile_api_ai/wechat_container.db',
    'mobile_api_ai/container_center.db',
    'wechat_container.db',
    'container_center.db'
]

for f in db_files:
    exists = os.path.exists(f)
    size = os.path.getsize(f) if exists else 0
    print(f"  {f}: {'存在' if exists else '不存在'} ({size} bytes if exists)")

# 检查 wechat_container.db 的表
print("\n" + "=" * 60)
print("wechat_container.db 表结构")
print("=" * 60)

if os.path.exists('mobile_api_ai/wechat_container.db'):
    conn = sqlite3.connect('mobile_api_ai/wechat_container.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"表数量: {len(tables)}")
    for t in tables:
        print(f"  - {t[0]}")

    # 检查 process_records 表
    try:
        cursor.execute('SELECT COUNT(*) FROM process_records')
        count = cursor.fetchone()[0]
        print(f"\nprocess_records 记录数: {count}")

        cursor.execute('SELECT id, order_no, order_no, status, source FROM process_records ORDER BY created_at DESC LIMIT 10')
        records = cursor.fetchall()
        print("\n最新10条:")
        for r in records:
            print(f"  {r}")

        # 检查 WO-202605008
        cursor.execute('SELECT id, order_no, order_no, status FROM process_records WHERE order_no LIKE ?', ('%202605008%',))
        wo008 = cursor.fetchall()
        print(f"\nWO-202605008: {'找到 ' + str(wo008) if wo008 else '未找到'}")

        # 检查 WO-202605007
        cursor.execute('SELECT id, order_no, order_no, status FROM process_records WHERE order_no LIKE ?', ('%202605007%',))
        wo007 = cursor.fetchall()
        print(f"WO-202605007: {'找到 ' + str(wo007) if wo007 else '未找到'}")

    except Exception as e:
        print(f"\nprocess_records 表错误: {e}")
    conn.close()
else:
    print("wechat_container.db 不存在")

print("\n" + "=" * 60)
