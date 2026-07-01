import requests, json

print("=== 验证两个页面 API ===")
print()

print("【调度中心】http://localhost:5003 流程排产界面")
try:
    r1 = requests.get('http://localhost:5003/api/dispatch-center/processes?t=1', timeout=10)
    data1 = r1.json()
    rows = data1.get('data', [])
    print(f"  /processes 返回 {len(rows)} 条:")
    for p in rows:
        wo = p.get('order_no', '') or p.get('workOrderNo', '')
        order = p.get('order_no', '') or p.get('orderNo', '')
        prod = p.get('product_name', '') or p.get('productName', '')
        src = p.get('source', '')
        print(f"    工单={wo}  订单={order}  产品={prod}  source={src}")
except Exception as e:
    print(f"  请求失败: {e}")

print()
print("【晨圣报工】http://localhost:5008 工单页面")
try:
    r2 = requests.get('http://localhost:5008/api/schedule/list?t=1', timeout=10)
    data2 = r2.json()
    items = data2.get('data', data2.get('items', []))
    print(f"  /schedule/list 返回 {len(items)} 条:")
    for p in items:
        wo = p.get('order_no', '') or p.get('workOrderNo', '')
        order = p.get('order_no', '') or p.get('orderNo', '')
        prod = p.get('product_name', '') or p.get('productName', '')
        print(f"    工单={wo}  订单={order}  产品={prod}")
except Exception as e:
    print(f"  请求失败: {e}")

print()
print("=== 数据库 process_records ===")
import sqlite3
db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute('SELECT order_no, order_no, product_name, quantity FROM process_records ORDER BY created_at DESC')
for r in c.fetchall():
    print(f"  工单={r[0]}  订单={r[1]}  产品={r[2]}  数量={r[3]}")
conn.close()
