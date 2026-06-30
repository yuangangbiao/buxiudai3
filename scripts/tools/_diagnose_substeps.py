"""
诊断脚本：直接查询 SQLite 数据库检查 sub_step 数据
"""
import sqlite3
import sys
import os

default_db = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          'mobile_api_ai', 'container_center.db')

db_path = sys.argv[1] if len(sys.argv) > 1 else default_db

print(f"数据库路径: {db_path}")
print(f"文件存在: {os.path.exists(db_path)}")
print()

if not os.path.exists(db_path):
    # 尝试查找
    for root, dirs, files in os.walk(os.path.dirname(os.path.dirname(__file__))):
        for f in files:
            if f.endswith('.db'):
                print(f"  找到数据库: {os.path.join(root, f)}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# 1. 检查表是否存在
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r['name'] for r in cursor.fetchall()]
print(f"数据库中的表: {tables}")
print()

if 'process_sub_steps' not in tables:
    print("❌ process_sub_steps 表不存在！")
    sys.exit(1)

# 2. 统计总数
cursor.execute("SELECT COUNT(*) as cnt FROM process_sub_steps")
total = cursor.fetchone()['cnt']
print(f"process_sub_steps 总记录数: {total}")
print()

# 3. 显示最新10条
cursor.execute("""
    SELECT id, process_id, order_no, step_name, batch_no,
           quantity, operator, created_at
    FROM process_sub_steps
    ORDER BY created_at DESC
    LIMIT 10
""")
rows = cursor.fetchall()
if rows:
    print("最新10条子步骤记录:")
    print("-" * 120)
    for r in rows:
        print(f"  id={r['id'][:8]}... process_id={r['process_id'][:8]}... "
              f"order={r['order_no']} step={r['step_name']} "
              f"qty={r['quantity']} op={r['operator']} "
              f"time={r['created_at']}")
else:
    print("⚠️ process_sub_steps 表为空！")
print()

# 4. 检查哪些 process_id 有关联
cursor.execute("SELECT DISTINCT process_id FROM process_sub_steps ORDER BY process_id")
pids = cursor.fetchall()
print(f"有子步骤的 process_id 数量: {len(pids)}")
for p in pids[:5]:
    pid = p['process_id']
    cursor.execute("SELECT COUNT(*) as cnt FROM process_sub_steps WHERE process_id = ?", (pid,))
    cnt = cursor.fetchone()['cnt']
    cursor.execute("SELECT order_no, step_name, created_at FROM process_sub_steps WHERE process_id = ? ORDER BY created_at DESC LIMIT 1", (pid,))
    last = cursor.fetchone()
    print(f"  process_id={pid[:8]}... 有{cnt}条, 最后: {last['order_no']} / {last['step_name']} / {last['created_at']}")

# 5. 检查 process_records 表
if 'process_records' in tables:
    cursor.execute("SELECT COUNT(*) as cnt FROM process_records")
    pr_count = cursor.fetchone()['cnt']
    print(f"\nprocess_records 总记录数: {pr_count}")
    
    # 显示最新几条
    cursor.execute("""
        SELECT id, order_no, current_step, status, created_at
        FROM process_records
        ORDER BY created_at DESC
        LIMIT 5
    """)
    for r in cursor.fetchall():
        cursor.execute("SELECT COUNT(*) as cnt FROM process_sub_steps WHERE process_id = ?", (r['id'],))
        sub_cnt = cursor.fetchone()['cnt']
        print(f"  订单 {r['order_no']} id={r['id'][:8]}... step={r['current_step']} sub_steps={sub_cnt}条")
    
    # 检查最新订单的子步骤
    cursor.execute("""
        SELECT id, order_no FROM process_records
        ORDER BY created_at DESC LIMIT 1
    """)
    latest = cursor.fetchone()
    if latest:
        pid = latest['id']
        order_no = latest['order_no']
        print(f"\n最新订单 {order_no} (id={pid[:8]}...) 的子步骤:")
        cursor.execute("""
            SELECT * FROM process_sub_steps WHERE process_id = ?
            ORDER BY created_at ASC
        """, (pid,))
        sub_steps = cursor.fetchall()
        if sub_steps:
            for s in sub_steps:
                print(f"  [{s['created_at']}] {s['step_name']} qty={s['quantity']} op={s['operator']} id={s['id'][:8]}...")
        else:
            print("  ❌ 没有任何子步骤！检查 process_id 是否匹配")

conn.close()
