import requests, sqlite3

out = []
def log(msg):
    out.append(str(msg))
    print(msg, flush=True)

log("=== 测试幂等性（直接SQL检查）===")

for i in range(3):
    r = requests.post('http://localhost:5002/api/schedule/publish',
        json={'order_no': 'WO-IDEM-003', 'order_no': f'ORD-IDEM-003-{i}',
              'product_name': '幂等测试3', 'quantity': 10, 'unit': '件',
              'plan_start': '2026-05-21', 'plan_end': '2026-05-31'}, timeout=10)
    d = r.json()
    log(f"第{i+1}次: code={d.get('code')} msg={d.get('message')}")

db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT id, order_no, order_no, created_at FROM process_records WHERE order_no='WO-IDEM-003'")
rows = c.fetchall()
log(f"数据库 WO-IDEM-003: {len(rows)} 条 (应为1)")
for r in rows:
    log(f"  id={r[0]} order={r[2]} created={r[3]}")
conn.close()

result_path = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\scripts\tools\idempotency_result.txt'
with open(result_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
log(f"结果已写入 {result_path}")
