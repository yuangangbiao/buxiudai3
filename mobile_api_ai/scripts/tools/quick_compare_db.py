"""快速对比数据库文件"""
import sqlite3
import os

files = [
    (r'D:\yuan\不锈钢网带跟单3.0\wechat_container.db', '根目录'),
    (r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db', 'mobile_api_ai'),
    (r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\data\wechat_container.db', 'mobile_api_ai\data'),
]

print("=" * 80)
print("数据库文件快速对比")
print("=" * 80)

for path, name in files:
    print(f"\n>>> {name}: {path}")
    if not os.path.exists(path):
        print("   ❌ 文件不存在")
        continue

    size = os.path.getsize(path)
    print(f"   ✅ 文件存在，大小: {size:,} 字节")

    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()

        # 获取表列表
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]

        print(f"   表数量: {len(tables)}")

        # 关键表记录数
        key_tables = ['process_sub_steps', 'process_records', 'data_packages', 'tasks']
        for table in key_tables:
            if table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"   - {table}: {count} 条记录")

                # 显示最新报工记录
                if table == 'process_sub_steps' and count > 0:
                    cur.execute(f"SELECT id, process_id, step_name, quantity, operator, created_at FROM {table} ORDER BY id DESC LIMIT 2")
                    rows = cur.fetchall()
                    for row in rows:
                        print(f"     最新: ID={row[0]} {row[2]} qty={row[3]} {row[4]} {row[5]}")

        conn.close()
    except Exception as e:
        print(f"   ❌ 读取错误: {e}")

print("\n" + "=" * 80)
print("对比结果：")
print("=" * 80)

# 统计报工记录总数
totals = []
for path, name in files:
    if not os.path.exists(path):
        continue
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM process_sub_steps")
        count = cur.fetchone()[0]
        totals.append((name, path, count))
        conn.close()
    except:
        pass

totals.sort(key=lambda x: x[2], reverse=True)

print(f"\n按报工记录数排序:")
for i, (name, path, count) in enumerate(totals, 1):
    print(f"  {i}. {name}: {count} 条报工记录")

print(f"\n🏆 数据最完整的数据库: {totals[0][0]}")
print(f"   路径: {totals[0][1]}")
