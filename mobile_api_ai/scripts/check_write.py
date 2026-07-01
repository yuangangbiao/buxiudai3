import sqlite3, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

mobile_api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(mobile_api_dir, 'wechat_container.db')

print('=== process_records 取样 ===')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT id, order_no, quantity, product_name FROM process_records ORDER BY created_at DESC LIMIT 10")
rows = cursor.fetchall()
for r in rows:
    d = dict(r)
    print(f"  id={d['id']} order_no={d['order_no']} qty={d['quantity']} product={d.get('product_name','')}")

print()
print('=== process_sub_steps 最近记录 ===')
cursor.execute("SELECT id, process_id, order_no, step_name, quantity, operator, created_at FROM process_sub_steps ORDER BY created_at DESC LIMIT 10")
rows = cursor.fetchall()
for r in rows:
    d = dict(r)
    print(f"  id={d['id'][:8]}... pid={d['process_id'][:8]}... order={d['order_no']} step={d['step_name']} qty={d['quantity']} operator={d['operator']} created={d['created_at']}")

# 按 process_id 统计各工序的已报工数量
print()
print('=== 各 process_id 的工序报工汇总 ===')
cursor.execute("""
    SELECT s.process_id, s.step_name, SUM(s.quantity) as reported,
           p.quantity as order_qty, p.order_no
    FROM process_sub_steps s
    LEFT JOIN process_records p ON s.process_id = p.id
    GROUP BY s.process_id, s.step_name
    ORDER BY s.process_id, s.step_name
    LIMIT 20
""")
rows = cursor.fetchall()
for r in rows:
    d = dict(r)
    reported = float(d['reported'])
    order_qty = float(d['order_qty']) if d['order_qty'] else 0
    status = 'OK' if order_qty == 0 or reported <= order_qty else f'超计划! (超{d["reported"]-order_qty})'
    print(f"  pid={d['process_id'][:8]}.. step={d['step_name']} reported={d['reported']} order_qty={order_qty} status={status}")

print()
print('=== 超计划检查：已报工>订单量 的工序 ===')
cursor.execute("""
    SELECT s.process_id, s.step_name, SUM(s.quantity) as reported,
           p.quantity as order_qty, p.order_no, p.product_name
    FROM process_sub_steps s
    LEFT JOIN process_records p ON s.process_id = p.id
    GROUP BY s.process_id, s.step_name
    HAVING reported > order_qty AND order_qty > 0
    ORDER BY (reported - order_qty) DESC
    LIMIT 10
""")
rows = cursor.fetchall()
for r in rows:
    d = dict(r)
    print(f"  pid={d['process_id'][:12]}.. order={d['order_no']} step={d['step_name']} reported={d['reported']} order_qty={d['order_qty']}")

# 模拟一次写入测试
print()
print('=== 模拟写入测试 ===')
try:
    cursor.execute('BEGIN IMMEDIATE')
    test_id = 'test-' + os.urandom(4).hex()
    test_pid = rows[0]['process_id'] if rows else 'test-pid'
    cursor.execute(
        "INSERT INTO process_sub_steps (id, process_id, order_no, step_name, batch_no, quantity, qualified_qty, operator, remark, equipment_name, overtime_hours, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (test_id, test_pid, 'TEST-ORDER', '测试工序', 'TEST-BATCH', 1.0, 1.0, '测试操作员', '', '', 0, '2026-01-01T00:00:00')
    )
    cursor.execute('ROLLBACK')
    print('  写入测试: ✅ 成功 (已回滚)')
except Exception as e:
    print(f'  写入测试: ❌ 失败 - {e}')

conn.close()
