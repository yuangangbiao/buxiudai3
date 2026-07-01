"""对比检查三个数据库的 sub_step 数据"""
import sqlite3
import json
import urllib.request

dbs = {
    '1. 当前项目 wechat_container.db': r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db',
    '2. 旧项目 wechat_container.db': 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\wechat_container.db',
    '3. container_center.db': r'D:\yuan\container_center.db',
}

order_no = 'ORD-202604210003'

for label, path in dbs.items():
    print(f'=== {label} ===')
    print(f'   路径: {path}')
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f'   表: {tables}')

    step_tables = [t for t in tables if 'sub_step' in t.lower() or 'step' in t.lower() or 'process' in t.lower() and 'sub' in t.lower()]
    for st in step_tables:
        cur.execute(f'SELECT COUNT(*) as cnt FROM "{st}"')
        cnt = cur.fetchone()['cnt']
        print(f'   {st}: {cnt} 条记录')

        if cnt > 0:
            cur.execute(f'SELECT * FROM "{st}" ORDER BY rowid DESC LIMIT 5')
            cols = [desc[0] for desc in cur.description]
            for row in cur.fetchall():
                row_data = dict(row)
                row_data.pop('source', None) if 'source' in row_data else None
                print(f'     {json.dumps(row_data, ensure_ascii=False, default=str)[:200]}')

    conn.close()
    print()

print('=== chengsheng.db sub_steps ===')
cs_path = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
conn = sqlite3.connect(cs_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT * FROM sub_steps WHERE order_no = ? ORDER BY created_at DESC', (order_no,))
rows = cur.fetchall()
print(f'   记录数: {len(rows)}')
for row in rows:
    print(f'     {json.dumps(dict(row), ensure_ascii=False, default=str)[:200]}')
conn.close()

print()
print('=== API /api/scan-info ===')
r = urllib.request.urlopen(f'http://localhost:5008/api/scan-info?code={order_no}')
data = json.loads(r.read())
print(f'   code: {data.get("code")}')
d = data.get('data', {})
print(f'   total_completed_qty: {d.get("total_completed_qty")}')
for p in d.get('processes', []):
    print(f'   {p["step_name"]}: completed_qty={p["completed_qty"]} / required_qty={p["required_qty"]}')

print()
print('=== API /api/sub_step_records ===')
r2 = urllib.request.urlopen(f'http://localhost:5008/api/sub_step_records?order_no={order_no}')
try:
    data2 = json.loads(r2.read())
    if isinstance(data2, list):
        print(f'   记录数: {len(data2)}')
        for r2 in data2:
            print(f'   {r2.get("processName")}: qty={r2.get("completedQty")}, worker={r2.get("worker")}')
    else:
        print(f'   {json.dumps(data2, ensure_ascii=False)[:300]}')
except Exception as e:
    print(f'   JSON解析失败: {e}, 原始数据: {r2.read().decode("utf-8")[:300]}')
