import requests, sqlite3, json, io, os

out = []
def log(msg):
    out.append(msg)
    print(msg)

try:
    log("开始发布 WO-202605008")
    r = requests.post('http://localhost:5002/api/schedule/publish',
        json={'order_no': 'WO-202605008', 'order_no': 'ORD-202605008',
              'product_name': '不锈钢网带', 'quantity': 100, 'unit': '件',
              'plan_start': '2026-05-21', 'plan_end': '2026-05-31'},
        timeout=10)
    d = r.json()
    log(f"container_center: {r.status_code} code={d.get('code')} msg={d.get('message')}")

    db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT order_no, order_no, created_at FROM process_records WHERE order_no='WO-202605008'")
    rows = c.fetchall()
    log(f"数据库: {len(rows)} 条")
    for r2 in rows:
        log(f"  wo={r2[0]} order={r2[1]} created={r2[2]}")
    conn.close()

    r2 = requests.get('http://localhost:5003/api/dispatch-center/processes?t=1', timeout=10)
    found = [p for p in r2.json().get('data',[]) if '202605008' in str(p.get('order_no',''))]
    log(f"调度中心: {len(found)} 条")
    for p in found:
        log(f"  wo={p.get('order_no')} order={p.get('order_no')}")

    r3 = requests.get('http://localhost:5008/api/schedule/list?t=1', timeout=10)
    items = r3.json().get('data', r3.json().get('items',[]))
    found2 = [p for p in items if '202605008' in str(p.get('order_no',''))]
    log(f"晨圣报工: {len(found2)} 条")
    for p in found2:
        log(f"  wo={p.get('order_no')} order={p.get('order_no')}")
except Exception as e:
    log(f"错误: {e}")
    import traceback
    traceback.print_exc()

result_path = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\scripts\tools\wo008_result.txt'
with open(result_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
log(f"结果已写入 {result_path}")
