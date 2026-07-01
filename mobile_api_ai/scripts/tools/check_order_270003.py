import sqlite3
import os
import json

os.chdir(r"d:\yuan\不锈钢网带跟单3.0\mobile_api_ai")

ORDER_NO = "ORD-202604270003"

print("=" * 60)
print(f"查询订单: {ORDER_NO}")
print("=" * 60)

# 1. wechat_container.db
print("\n[1] wechat_container.db")
conn = sqlite3.connect('wechat_container.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# process_records
cur.execute("SELECT * FROM process_records WHERE order_no = ?", (ORDER_NO,))
rec = cur.fetchone()
if rec:
    print(f"\n  process_records: ✅")
    print(f"    id: {rec['id']}")
    print(f"    order_no: {rec['order_no']}")
    print(f"    product_name: {rec['product_name']}")
    print(f"    quantity: {rec['quantity']}")
    print(f"    unit: {rec.get('unit', 'N/A')}")
    print(f"    status: {rec['status']}")
    print(f"    current_step: {rec.get('current_step', 'N/A')}")
    print(f"    customer_name: {rec.get('customer_name', 'N/A')}")
    print(f"    created_at: {rec.get('created_at', 'N/A')}")

    pid = rec['id']

    # steps
    steps = rec.get('steps', '')
    if steps:
        try:
            steps_json = json.loads(steps) if isinstance(steps, str) else steps
            print(f"\n    工序列表 ({len(steps_json)}个):")
            for i, s in enumerate(steps_json):
                if isinstance(s, dict):
                    print(f"      [{i}] {s.get('name', 'N/A')} | role={s.get('role', 'N/A')} | status={s.get('status_key', 'N/A')}")
                else:
                    print(f"      [{i}] {s}")
        except Exception as e:
            print(f"    steps解析错误: {e}")
else:
    print("\n  process_records: ❌ 未找到")
    pid = None

    cur.execute("SELECT order_no, id, status FROM process_records WHERE order_no LIKE ?", (f"%{ORDER_NO[-8:]}%",))
    similar = cur.fetchall()
    if similar:
        print(f"\n  类似订单:")
        for s in similar:
            print(f"    {s[0]} | id={s[1]} | status={s[2]}")
    else:
        print(f"\n  无类似订单")

# process_sub_steps
print("\n  process_sub_steps:")
if pid:
    cur.execute("SELECT COUNT(*) FROM process_sub_steps WHERE process_id = ?", (pid,))
    cnt = cur.fetchone()[0]
    print(f"    按process_id: {cnt} 条")

    if cnt > 0:
        cur.execute("""
            SELECT step_name, SUM(quantity) as total_qty, COUNT(*) as cnt
            FROM process_sub_steps WHERE process_id = ?
            GROUP BY step_name
        """, (pid,))
        print(f"\n    工序汇总:")
        for r in cur.fetchall():
            print(f"      {r[0]}: qty={r[1]} (共{r[2]}条)")

        cur.execute("SELECT * FROM process_sub_steps WHERE process_id = ? ORDER BY created_at DESC LIMIT 10", (pid,))
        print(f"\n    最近10条记录:")
        for s in cur.fetchall():
            print(f"      step={s['step_name']} qty={s['quantity']} op={s.get('operator','N/A')} time={s.get('created_at')}")

    # 也按 order_no 查
    cur.execute("SELECT COUNT(*) FROM process_sub_steps WHERE order_no = ?", (ORDER_NO,))
    cnt2 = cur.fetchone()[0]
    print(f"\n    按order_no: {cnt2} 条")
else:
    print("    (无process_id)")

# data_packages
cur.execute("SELECT COUNT(*) FROM data_packages WHERE related_order = ?", (ORDER_NO,))
pkg_cnt = cur.fetchone()[0]
print(f"\n  data_packages: {pkg_cnt} 条")

if pkg_cnt > 0:
    cur.execute("SELECT * FROM data_packages WHERE related_order = ? ORDER BY created_at DESC LIMIT 5", (ORDER_NO,))
    for p in cur.fetchall():
        print(f"    type={p.get('data_type')} title={p.get('title')} status={p.get('status')}")

conn.close()

# 2. chengsheng.db
print("\n" + "-" * 40)
print("[2] chengsheng.db")

if os.path.exists('chengsheng.db'):
    conn = sqlite3.connect('chengsheng.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # orders
    cur.execute("SELECT * FROM orders WHERE order_no = ?", (ORDER_NO,))
    o = cur.fetchone()
    if o:
        print(f"\n  orders: ✅")
        print(f"    order_id: {o['order_id']}")
        print(f"    order_no: {o['order_no']}")
        print(f"    name: {o['name']}")
        print(f"    quantity: {o['quantity']}")
        print(f"    status: {o['status']}")
    else:
        print(f"\n  orders: ❌ 未找到")

    # sub_steps
    cur.execute("SELECT COUNT(*) FROM sub_steps WHERE order_no = ?", (ORDER_NO,))
    cnt = cur.fetchone()[0]
    print(f"\n  sub_steps: {cnt} 条")

    if cnt > 0:
        cur.execute("""
            SELECT step_name, SUM(quantity) as total_qty, COUNT(*) as cnt
            FROM sub_steps WHERE order_no = ?
            GROUP BY step_name
        """, (ORDER_NO,))
        print(f"\n    工序汇总:")
        for r in cur.fetchall():
            print(f"      {r[0]}: qty={r[1]} (共{r[2]}条)")

        cur.execute("SELECT * FROM sub_steps WHERE order_no = ? ORDER BY created_at DESC LIMIT 10", (ORDER_NO,))
        print(f"\n    最近10条:")
        for s in cur.fetchall():
            print(f"      step={s['step_name']} qty={s['quantity']} op={s.get('operator')} synced={s.get('synced')}")

    conn.close()
else:
    print("\n  chengsheng.db: 不存在")

print("\n" + "=" * 60)
print("完成")
print("=" * 60)
