"""对比检查 ORD-202604290001 在三个数据库的最新数据"""
import sqlite3
import json
import urllib.request

order_no = 'ORD-202604290001'

# 1. 容器中心 wechat_container.db
print(f'=== 容器中心 wechat_container.db ===')
path = r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT * FROM process_sub_steps WHERE order_no = ? ORDER BY rowid DESC', (order_no,))
rows = cur.fetchall()
print(f'   process_sub_steps 记录数: {len(rows)}')
for row in rows[:10]:
    d = dict(row)
    print(f'   id={d["id"][:8]} process_id={str(d.get("process_id",""))[:8]} step={d["step_name"]} qty={d.get("quantity")} created_at={str(d.get("created_at",""))[:19]}')
conn.close()

# 2. chengsheng.db sub_steps
print(f'\n=== chengsheng.db sub_steps ===')
cs_path = 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db'
conn = sqlite3.connect(cs_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT * FROM sub_steps WHERE order_no = ? ORDER BY created_at DESC', (order_no,))
rows = cur.fetchall()
print(f'   记录数: {len(rows)}')
for row in rows:
    d = dict(row)
    print(f'   id={d["id"]} step_id={str(d.get("step_id",""))[:8]} step={d["step_name"]} qty={d["quantity"]} time={str(d.get("created_at",""))[:19]}')
conn.close()

# 3. API /api/scan-info
print(f'\n=== API /api/scan-info ===')
r = urllib.request.urlopen(f'http://localhost:5008/api/scan-info?code={order_no}')
data = json.loads(r.read())
d = data.get('data', {})
print(f'   total_completed_qty: {d.get("total_completed_qty")}')
for p in d.get('processes', []):
    if p['completed_qty'] > 0:
        print(f'   {p["step_name"]}: completed_qty={p["completed_qty"]} / required_qty={p["required_qty"]}')

# 4. API /api/sub_step_records
print(f'\n=== API /api/sub_step_records ===')
r2 = urllib.request.urlopen(f'http://localhost:5008/api/sub_step_records?order_no={order_no}')
try:
    data2 = json.loads(r2.read())
    if isinstance(data2, list):
        print(f'   记录数: {len(data2)}')
        for rec in data2:
            print(f'   {rec.get("processName")}: qty={rec.get("completedQty")}, worker={rec.get("worker")}, time={str(rec.get("time",""))[:19]}')
    else:
        print(f'   {json.dumps(data2, ensure_ascii=False)[:300]}')
except Exception as e:
    print(f'   错误: {e}')
