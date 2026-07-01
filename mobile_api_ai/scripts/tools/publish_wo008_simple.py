import requests, sqlite3, sys
sys.stdout = open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\scripts\tools\wo008_result.txt', 'w')
sys.stderr = sys.stdout

r = requests.post('http://localhost:5002/api/schedule/publish',
    json={'order_no': 'WO-202605008', 'order_no': 'ORD-202605008',
          'product_name': '不锈钢网带', 'quantity': 100, 'unit': '件',
          'plan_start': '2026-05-21', 'plan_end': '2026-05-31'},
    timeout=10)
d = r.json()
print(f'container_center: status={r.status_code} code={d.get("code")} msg={d.get("message")}')

conn = sqlite3.connect(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db')
c = conn.cursor()
c.execute("SELECT order_no, order_no, created_at FROM process_records WHERE order_no='WO-202605008'")
rows = c.fetchall()
print(f'数据库: {len(rows)} 条')
for r in rows:
    print(f'  wo={r[0]} order={r[1]} created={r[2]}')
conn.close()

r2 = requests.get('http://localhost:5003/api/dispatch-center/processes?t=1', timeout=10)
found = [p for p in r2.json().get('data',[]) if '202605008' in str(p.get('order_no',''))]
print(f'调度中心: {len(found)} 条')

r3 = requests.get('http://localhost:5008/api/schedule/list?t=1', timeout=10)
items = r3.json().get('data', r3.json().get('items',[]))
found2 = [p for p in items if '202605008' in str(p.get('order_no',''))]
print(f'晨圣报工: {len(found2)} 条')

sys.stdout.close()
