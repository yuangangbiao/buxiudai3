import sqlite3, json, os

print("=== 追踪 WO-202605007 ===")
print()

db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()

# 1. process_records
print("【1】process_records")
c.execute("SELECT id, order_no, order_no, product_name, created_at FROM process_records WHERE order_no LIKE '%202605007%' OR order_no LIKE '%202605007%'")
rows = c.fetchall()
print(f"  找到 {len(rows)} 条")
for r in rows:
    print(f"    wo={r[1]}  order={r[2]}  product={r[3]}  created={r[4]}")

# 2. data_packages work_order
print()
print("【2】data_packages (work_order)")
c.execute("SELECT id, data_type, title, related_order, created_at FROM data_packages WHERE data_type='work_order'")
rows2 = c.fetchall()
print(f"  共 {len(rows2)} 条:")
for r in rows2:
    print(f"    id={r[0]}  title={r[2]}  order={r[3]}  created={r[4]}")

conn.close()

# 3. dispatch_center_data.json
print()
print("【3】dispatch_center_data.json (项目根目录)")
jpath = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center_data.json'
if os.path.exists(jpath):
    with open(jpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    procs = data.get('processes', [])
    print(f"  共 {len(procs)} 条:")
    for p in procs:
        print(f"    wo={p.get('order_no')}  order={p.get('order_no')}  product={p.get('product_name')}")
else:
    print("  文件不存在")

# 4. system.db DocumentStore
print()
print("【5】system.db DocumentStore")
db2 = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\data\system.db'
if os.path.exists(db2):
    conn2 = sqlite3.connect(db2)
    c2 = conn2.cursor()
    c2.execute("SELECT COUNT(*) FROM tbl_documents")
    total = c2.fetchone()[0]
    print(f"  总记录: {total}")
    c2.execute("SELECT id, doc_type, doc_data, created_at FROM tbl_documents")
    for r in c2.fetchall():
        try:
            dd = json.loads(r[2])
            procs3 = dd.get('processes', [])
            print(f"    id={r[0]}  type={r[1]}  processes={len(procs3)}:")
            for p in procs3:
                print(f"      wo={p.get('order_no')}  order={p.get('order_no')}")
        except Exception as e:
            print(f"    id={r[0]}  type={r[1]}  (无法解析: {e})")
    conn2.close()
else:
    print("  system.db 不存在")

print()
print("=== 所有位置都没有 WO-202605007 ===")
