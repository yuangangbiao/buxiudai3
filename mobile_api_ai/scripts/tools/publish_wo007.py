import sys
sys.stdout = open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\scripts\tools\wo007_out.txt', 'w', encoding='utf-8', buffering=1)
sys.stderr = sys.stdout

import requests, json

print("=== 模拟发布 WO-202605007 ===")

try:
    r = requests.post(
        'http://localhost:5002/api/schedule/publish',
        json={
            'order_no': 'WO-202605007',
            'order_no': 'ORD-202605007',
            'product_name': '测试产品007',
            'quantity': 200,
            'unit': '件',
            'plan_start': '2026-05-21',
            'plan_end': '2026-05-31',
            'customer_name': '测试客户007',
            'notes': '诊断测试007'
        },
        timeout=10
    )
    data = r.json()
    print(f"POST result: status={r.status_code} code={data.get('code')} msg={data.get('message')}")
except Exception as e:
    print(f"POST failed: {e}")

import sqlite3
db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT id, order_no, order_no, product_name, created_at FROM process_records WHERE order_no='WO-202605007'")
rows = c.fetchall()
print(f"process_records found: {len(rows)}")
for r in rows:
    print(f"  wo={r[1]} order={r[2]} product={r[3]} created={r[4]}")
conn.close()

sys.stdout.close()
sys.stdout = sys.__stdout__
print("Done - see wo007_out.txt")
