import sqlite3, json
db = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\data\system.db'
conn = sqlite3.connect(db)
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print('=== 表列表 ===')
for t in tables:
    print(f'  {t[0]}')

c.execute("SELECT id, doc_type, created_at, updated_at FROM tbl_documents WHERE id='dispatch_center_data'")
row = c.fetchone()
if row:
    print('\n=== dispatch_center_data 文档信息 ===')
    print(f'ID: {row[0]}, Type: {row[1]}, Created: {row[2]}, Updated: {row[3]}')
    c.execute("SELECT doc_data FROM tbl_documents WHERE id='dispatch_center_data'")
    data = c.fetchone()[0]
    parsed = json.loads(data)
    print(f'根键: {list(parsed.keys())}')
    print(f'processes 数量: {len(parsed.get("processes", []))}')
    if parsed.get('processes'):
        for p in parsed['processes']:
            print(f'  - ID: {p.get("id","")}, 订单号: {p.get("order_no","")}, 订单: {p.get("order_no","")}')
    else:
        print('  (空)')
    print(f'rules 数量: {len(parsed.get("rules", []))}')
    print(f'operators 数量: {len(parsed.get("operators", []))}')
else:
    print('\n未找到 dispatch_center_data 文档')

c.execute("SELECT COUNT(*) FROM tbl_documents")
cnt = c.fetchone()[0]
print(f'\ntbl_documents 总记录数: {cnt}')

conn.close()
print('\n查询完成')
