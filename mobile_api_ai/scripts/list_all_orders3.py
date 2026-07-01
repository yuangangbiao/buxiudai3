import sqlite3

db = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

# 生产工单详情
print('=== process_records 生产工单详情 ===')
for wo in ['WO-202605005','WO-202605006','WO-202605007','WO-202605008','WO-202605009','WO-2026-002']:
    rows = conn.execute("SELECT * FROM process_records WHERE order_no=? ORDER BY id", (wo,)).fetchall()
    if rows:
        for r in rows:
            d = dict(r)
            print(f'  {wo}: product={d["product_name"]} qty={d["quantity"]} customer={d["customer_name"]} status={d["status"]} created={d["created_at"]}')

# ORD-202604 工单
print('\n=== ORD 生产工单详情 ===')
for wo in ['ORD-202604210001','ORD-202604210002','ORD-202604210003','ORD-202604270001','ORD-202604270003','ORD-202604270004','ORD-202604290001','ORD-20260416-0002']:
    rows = conn.execute("SELECT * FROM process_records WHERE order_no=? ORDER BY id", (wo,)).fetchall()
    if rows:
        for r in rows:
            d = dict(r)
            print(f'  {wo}: product={d["product_name"]} qty={d["quantity"]} customer={d["customer_name"]} status={d["status"]} created={d["created_at"]}')
    else:
        # 检查data_packages
        dp = conn.execute("SELECT COUNT(*) as cnt, MIN(created_at) as first, MAX(created_at) as last FROM data_packages WHERE related_order=?", (wo,)).fetchone()
        if dp and dp['cnt'] > 0:
            print(f'  {wo}: 仅 data_packages {dp["cnt"]}条, {dp["first"]}~{dp["last"]}')

conn.close()
