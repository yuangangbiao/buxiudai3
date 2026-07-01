import sqlite3

db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()

print("=== 清理 WO-202605008 重复记录 ===")

c.execute("""
    SELECT id, order_no, order_no, created_at
    FROM process_records
    WHERE order_no = 'WO-202605008'
    ORDER BY created_at ASC
""")
rows = c.fetchall()
print(f"WO-202605008 记录总数: {len(rows)}")

if len(rows) > 1:
    # 保留最新的一条
    keep_id = rows[-1][0]
    delete_ids = [r[0] for r in rows[:-1]]
    print(f"保留: id={keep_id} created={rows[-1][3]}")
    print(f"删除: {len(delete_ids)} 条")
    for r in rows[:-1]:
        print(f"  删除 id={r[0]} created={r[3]}")

    placeholders = ','.join(['?'] * len(delete_ids))
    c.execute(f"DELETE FROM process_records WHERE id IN ({placeholders})", delete_ids)
    deleted = c.rowcount
    conn.commit()
    print(f"实际删除: {deleted} 条")
elif len(rows) == 1:
    print("只有1条，无需清理")
else:
    print("没有记录")

# 验证
c.execute("SELECT id, order_no, order_no, created_at FROM process_records WHERE order_no='WO-202605008'")
rows2 = c.fetchall()
print(f"\n清理后剩余: {len(rows2)} 条")
for r in rows2:
    print(f"  id={r[0]} wo={r[1]} order={r[2]} created={r[3]}")

conn.close()
print("\n清理完成")
