import sqlite3, json

conn = sqlite3.connect('D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\data\\system.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check all tbl_documents
cur.execute('SELECT * FROM tbl_documents')
rows = cur.fetchall()
print(f'Total documents in system.db: {len(rows)}')
for row in rows:
    d = dict(row)
    print(f'\n--- Document: {d["id"]} ---')
    print(f'  doc_type: {d["doc_type"]}')
    print(f'  status: {d["status"]}')
    print(f'  created_at: {d["created_at"]}')
    print(f'  updated_at: {d["updated_at"]}')
    try:
        doc_data = json.loads(d['doc_data'])
        print(f'  keys: {list(doc_data.keys())}')
        for k, v in doc_data.items():
            if isinstance(v, list):
                print(f'  {k}: {len(v)} items')
                if k == 'processes' and v:
                    for p in v[:3]:
                        print(f'    - {p.get("id", "")} | order: {p.get("order_no", "")} | status: {p.get("status", "")}')
            elif isinstance(v, dict):
                print(f'  {k}: {len(v)} keys')
            else:
                print(f'  {k}: {str(v)[:100]}')
    except Exception as e:
        print(f'  parse error: {e}')

conn.close()
