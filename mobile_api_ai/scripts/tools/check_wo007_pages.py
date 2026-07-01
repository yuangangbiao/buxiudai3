import sys
sys.stdout = open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\scripts\tools\wo007_check.txt', 'w', encoding='utf-8', buffering=1)
sys.stderr = sys.stdout

import requests

print("=== 检查 WO-202605007 在两个页面的情况 ===")

# 1. 调度中心
print("\n[1] 调度中心 5003 /processes")
try:
    r = requests.get('http://localhost:5003/api/dispatch-center/processes?t=1', timeout=10)
    data = r.json()
    rows = data.get('data', [])
    found = [p for p in rows if '202605007' in str(p.get('order_no',''))]
    print(f"  总返回 {len(rows)} 条，含 WO-202605007: {len(found)} 条")
    for p in found:
        wo = p.get('order_no','')
        order = p.get('order_no','')
        prod = p.get('product_name','')
        src = p.get('source','')
        print(f"    wo={wo} order={order} product={prod} source={src}")
    if not found:
        print("  *** WO-202605007 未在调度中心显示 ***")
        print(f"  最近3条:")
        for p in rows[:3]:
            print(f"    wo={p.get('order_no')} order={p.get('order_no')}")
except Exception as e:
    print(f"  失败: {e}")

# 2. 晨圣报工
print("\n[2] 晨圣报工 5008 /schedule/list")
try:
    r = requests.get('http://localhost:5008/api/schedule/list?t=1', timeout=10)
    data = r.json()
    items = data.get('data', data.get('items', data.get('list', [])))
    found2 = [p for p in items if '202605007' in str(p.get('order_no',''))]
    print(f"  总返回 {len(items)} 条，含 WO-202605007: {len(found2)} 条")
    for p in found2:
        wo = p.get('order_no','')
        order = p.get('order_no','')
        prod = p.get('product_name','')
        print(f"    wo={wo} order={order} product={prod}")
    if not found2:
        print("  *** WO-202605007 未在晨圣报工显示 ***")
except Exception as e:
    print(f"  失败: {e}")

# 3. 数据库确认
print("\n[3] 数据库 process_records")
import sqlite3
db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT id, order_no, order_no, product_name, created_at FROM process_records WHERE order_no='WO-202605007'")
rows = c.fetchall()
print(f"  数据库中 WO-202605007 记录数: {len(rows)}")
for r in rows:
    print(f"    wo={r[1]} order={r[2]} product={r[3]} created={r[4]}")
conn.close()

sys.stdout.close()
sys.stdout = sys.__stdout__
print("Done - see wo007_check.txt")
