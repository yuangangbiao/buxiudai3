import sqlite3

db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()

print("=== 清理测试工单 ===")

# 清理 WO-IDEM-001
c.execute("DELETE FROM process_records WHERE order_no='WO-IDEM-001'")
print(f"WO-IDEM-001: 删除 {c.rowcount} 条")

# 清理 WO-REAL-TIME
c.execute("DELETE FROM process_records WHERE order_no='WO-REAL-TIME'")
print(f"WO-REAL-TIME: 删除 {c.rowcount} 条")

# 清理 WO-TEST-VERIFY
c.execute("DELETE FROM process_records WHERE order_no='WO-TEST-VERIFY'")
print(f"WO-TEST-VERIFY: 删除 {c.rowcount} 条")

# 清理 WO-REAL-TEST
c.execute("DELETE FROM process_records WHERE order_no='WO-REAL-TEST'")
print(f"WO-REAL-TEST: 删除 {c.rowcount} 条")

conn.commit()

# 验证
c.execute("SELECT COUNT(*) FROM process_records")
print(f"\nprocess_records 总数: {c.fetchone()[0]} 条")

c.execute("SELECT id, order_no, order_no, product_name, created_at FROM process_records ORDER BY created_at DESC")
rows = c.fetchall()
print("当前所有记录:")
for r in rows:
    print(f"  wo={r[1]} order={r[2]} product={r[3]} created={r[4]}")

conn.close()
print("\n清理完成")
