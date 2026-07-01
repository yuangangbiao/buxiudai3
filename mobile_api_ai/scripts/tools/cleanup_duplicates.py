import sqlite3

db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()

print("=== 清理所有重复工单 ===")

# 找出所有 order_no 的重复记录
c.execute("SELECT order_no, COUNT(*) as cnt FROM process_records GROUP BY order_no HAVING cnt > 1")
dups = c.fetchall()
print(f"发现重复订单: {len(dups)} 个")
for dup in dups:
    wo = dup[0]
    cnt = dup[1]
    c.execute("SELECT id, order_no, order_no, created_at FROM process_records WHERE order_no=? ORDER BY created_at ASC", (wo,))
    rows = c.fetchall()
    print(f"\n{wo}: {cnt} 条重复")
    keep_id = rows[-1][0]
    delete_ids = [r[0] for r in rows[:-1]]
    print(f"  保留: id={keep_id} created={rows[-1][3]}")
    print(f"  删除: {len(delete_ids)} 条")

    placeholders = ','.join(['?'] * len(delete_ids))
    c.execute(f"DELETE FROM process_records WHERE id IN ({placeholders})", delete_ids)
    print(f"  实际删除: {c.rowcount} 条")

conn.commit()

# 验证
print("\n=== 验证最终状态 ===")
c.execute("SELECT order_no, COUNT(*) FROM process_records GROUP BY order_no")
rows = c.fetchall()
print("工单数量统计:")
for r in rows:
    print(f"  {r[0]}: {r[1]} 条")

c.execute("SELECT id, order_no, order_no, product_name, created_at FROM process_records ORDER BY created_at DESC")
all_rows = c.fetchall()
print(f"\n总计: {len(all_rows)} 条")
for r in all_rows:
    print(f"  wo={r[1]} order={r[2]} product={r[3]} created={r[4]}")

conn.close()
print("\n完成")
