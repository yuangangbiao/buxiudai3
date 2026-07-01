import sqlite3

db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()

# 清理所有测试工单
test_wos = ['WO-IDEM-001', 'WO-IDEM-002', 'WO-REAL-TIME', 'WO-TEST-VERIFY', 'WO-REAL-TEST']
for wo in test_wos:
    c.execute("DELETE FROM process_records WHERE order_no=?", (wo,))
    if c.rowcount > 0:
        print(f"删除 {wo}: {c.rowcount} 条")

conn.commit()
c.execute("SELECT COUNT(*) FROM process_records")
print(f"process_records 总数: {c.fetchone()[0]}")
c.execute("SELECT id, order_no, order_no, product_name FROM process_records ORDER BY created_at DESC")
for r in c.fetchall():
    print(f"  wo={r[1]} order={r[2]} product={r[3]}")
conn.close()
