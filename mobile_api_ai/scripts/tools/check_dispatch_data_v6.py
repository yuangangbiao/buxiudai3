"""
验证 process_id 不一致问题
"""
import urllib.request, json, sqlite3, os, sys

sys.stdout.reconfigure(encoding='utf-8')

def fetch_json(url):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        return json.loads(r.read().decode())
    except Exception as e:
        return {'_error': str(e)}

BASE = 'http://127.0.0.1:5008'
order = 'ORD-202604290001'

# 1. 获取 dispatch center 的 process_id
d = fetch_json(f'{BASE}/api/dispatch-center/processes')
if isinstance(d, dict) and d.get('code') == 0:
    processes = d.get('data', [])
else:
    processes = d if isinstance(d, list) else []
target = next((p for p in processes if order in p.get('order_no','')), None)
dispatch_pid = target.get('id','') if target else '(none)'
print(f'调度中心 process_id: {dispatch_pid}')

# 2. 从 chengsheng.db 查 process_records 看该订单的 process_id
db_path = os.getenv('CHENGSHENG_DB_PATH', 'D:\\yuan\\不锈钢网带跟单3.0\\mobile_api_ai\\chengsheng.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT id, order_no, product_name, quantity, steps FROM process_records WHERE order_no = ?", (order,))
rows = cur.fetchall()
print(f'\nchengsheng.db process_records: {len(rows)} 条')
for r in rows:
    d = dict(r)
    pid = d['id']
    print(f'  id={pid}')
    print(f'  order_no={d["order_no"]}')
    print(f'  product_name={d["product_name"]}')
    print(f'  quantity={d["quantity"]}')

# 3. 从 wechat_container.db 查 sub_steps
wc_path = os.path.join(os.path.dirname(db_path), 'wechat_container.db')
if os.path.exists(wc_path):
    conn2 = sqlite3.connect(wc_path)
    conn2.row_factory = sqlite3.Row
    cur2 = conn2.cursor()
    cur2.execute("SELECT * FROM process_sub_steps WHERE order_no = ?", (order,))
    sub_rows = cur2.fetchall()
    print(f'\nwechat_container.db process_sub_steps: {len(sub_rows)} 条')
    for r in sub_rows:
        d = dict(r)
        pid = d.get('process_id','')
        print(f'  step_name={d.get("step_name","?")} qty={d.get("quantity","?")} process_id={pid}')
else:
    print(f'\nwechat_container.db not found at {wc_path}')

# 4. 检查 dispatch_center_data.json 中的 process_id
dc_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'dispatch_center_data.json')
if os.path.exists(dc_data):
    with open(dc_data, 'r', encoding='utf-8') as f:
        dc_json = json.load(f)
    for proc in dc_json.get('processes', []):
        if order in proc.get('order_no', ''):
            print(f'\ndispatch_center_data.json process:')
            print(f'  id={proc.get("id","")}')
            print(f'  order_no={proc.get("order_no","")}')
            print(f'  order_no={proc.get("order_no","")}')
            print(f'  step_name={proc.get("step_name","")}')
            print(f'  status={proc.get("status","")}')
else:
    print(f'\ndispatch_center_data.json not found at {dc_data}')

conn.close()
print('\n检查完成')
