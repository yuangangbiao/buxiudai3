"""
清除所有测试数据，保留桌面端真实工单

保留:
  - WO-202605005 (ORD-202604210003) 冷冻螺旋网 1000件
  - WO-202605006 (ORD-202604290001) 平板型网带 50件
  - WO-202605003 (ORD-202604220001) 60件

清理范围:
  1. wechat_container.db process_records 表
  2. dispatch_center_data.json (项目根目录)
  3. data_packages 表中的 work_order 文档
  4. data/system.db DocumentStore 中的 dispatch_center_data 文档
"""
import sqlite3, json, os

# 保留的真实订单号列表
KEEP_WORK_ORDER_NOS = ['WO-202605005', 'WO-202605006', 'WO-202605003']

def _clean_dispatch_documents(system_db_path, label):
    """清理 DocumentStore (system.db) 中的 dispatch_center_data 文档"""
    if not os.path.exists(system_db_path):
        return
    conn = sqlite3.connect(system_db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tbl_documents")
    total = c.fetchone()[0]
    c.execute("SELECT id, doc_type, created_at FROM tbl_documents WHERE id='dispatch_center_data'")
    rows = c.fetchall()
    if rows:
        c.execute("DELETE FROM tbl_documents WHERE id='dispatch_center_data'")
        deleted = c.rowcount
        conn.commit()
        print(f"  [{label}] 已删除 {deleted} 条 dispatch_center_data 文档")
    conn.close()

def _clean_dispatch_json(json_path, label):
    """清理 dispatch_center_data.json"""
    if not os.path.exists(json_path):
        return
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    old = data.get('processes', [])
    new = [p for p in old if p.get('order_no', '') in KEEP_WORK_ORDER_NOS]
    data['processes'] = new
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [{label}] dispatch_center_data.json: {len(old)} → {len(new)} 条")

# === 1. 清理 wechat_container.db process_records ===
db_path = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM process_records")
before = c.fetchone()[0]
c.execute("""
    DELETE FROM process_records
    WHERE order_no IS NULL
       OR (order_no NOT IN ({})
           AND order_no NOT LIKE 'WO-2026%')
""".format(','.join(['?']*len(KEEP_WORK_ORDER_NOS))), KEEP_WORK_ORDER_NOS)
deleted = c.rowcount
c.execute("SELECT COUNT(*) FROM process_records")
after = c.fetchone()[0]
print(f"[SQLite] process_records: {before} → {after} 条 (删除 {deleted} 条)")
conn.commit()
conn.close()

# === 2. 清理 data_packages work_order 文档 ===
conn2 = sqlite3.connect(db_path)
c2 = conn2.cursor()
c2.execute("SELECT COUNT(*) FROM data_packages WHERE data_type='work_order'")
wo_count = c2.fetchone()[0]
if wo_count > 0:
    c2.execute("DELETE FROM data_packages WHERE data_type='work_order'")
    deleted_wo = c2.rowcount
    print(f"[data_packages] 已删除 {deleted_wo} 条 work_order 文档")
c2.execute("SELECT data_type, COUNT(*) FROM data_packages GROUP BY data_type")
for r in c2.fetchall():
    print(f"  {r[0]}: {r[1]}条")
conn2.close()

# === 3. 清理 dispatch_center_data.json (项目根目录) ===
_clean_dispatch_json(
    r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center_data.json',
    'mobile_api_ai')
_clean_dispatch_json(
    r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\data\dispatch_center_data.json',
    'mobile_api_ai/data')

# === 4. 清理 DocumentStore system.db (项目目录) ===
_clean_dispatch_documents(
    r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\data\system.db',
    'mobile_api_ai/data')

print("\n=== 清理完成 ===")
print("请重启 container_center_api (5002) 和 wechat_server (5003) 服务")
print("重启后调度中心流程排产界面只显示桌面端工单数据，不再包含测试工单")
