import requests, json, sys

print("=== 发布 WO-202605008 到 container_center ===")

result = requests.post(
    'http://localhost:5002/api/schedule/publish',
    json={
        'order_no': 'WO-202605008',
        'order_no': 'ORD-202605008',
        'product_name': '不锈钢网带',
        'quantity': 100,
        'unit': '件',
        'plan_start': '2026-05-21',
        'plan_end': '2026-05-31',
        'customer_name': '客户',
        'notes': '从调度中心重新发布'
    },
    timeout=10
)
data = result.json()
print(f"container_center 响应: status={result.status_code} code={data.get('code')} msg={data.get('message')}")

# 验证
import sqlite3
db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT order_no, order_no, product_name, created_at FROM process_records WHERE order_no='WO-202605008'")
rows = c.fetchall()
print(f"数据库写入: {len(rows)} 条")
for r in rows:
    print(f"  wo={r[0]} order={r[1]} product={r[2]} created={r[3]}")
conn.close()

# 调度中心
r2 = requests.get('http://localhost:5003/api/dispatch-center/processes?t=1', timeout=10)
d2 = r2.json()
found = [p for p in d2.get('data',[]) if '202605008' in str(p.get('order_no',''))]
print(f"调度中心显示: {len(found)} 条")

# 晨圣报工
r3 = requests.get('http://localhost:5008/api/schedule/list?t=1', timeout=10)
d3 = r3.json()
items = d3.get('data', d3.get('items', []))
found2 = [p for p in items if '202605008' in str(p.get('order_no',''))]
print(f"晨圣报工显示: {len(found2)} 条")

print("=== 完成 ===")
