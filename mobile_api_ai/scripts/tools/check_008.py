import sys
sys.stdout = open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\scripts\tools\check_008.txt', 'w', encoding='utf-8', buffering=1)
sys.stderr = sys.stdout

import sqlite3, requests

db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()

print("=== 检查 WO-202605008 ===")

# 1. 数据库
c.execute("""
    SELECT id, order_no, order_no, product_name, created_at
    FROM process_records
    WHERE order_no = 'WO-202605008'
""")
rows = c.fetchall()
print(f"[数据库] WO-202605008: {len(rows)} 条")
for r in rows:
    print(f"  wo={r[1]} order={r[2]} product={r[3]} created={r[4]}")

conn.close()

# 2. 调度中心
print()
print("[调度中心 5003]")
try:
    r = requests.get('http://localhost:5003/api/dispatch-center/processes?t=1', timeout=10)
    data = r.json()
    rows2 = data.get('data', [])
    found = [p for p in rows2 if '202605008' in str(p.get('order_no',''))]
    print(f"  总{len(rows2)}条，含008: {len(found)}条")
    for p in found:
        print(f"  wo={p.get('order_no')} order={p.get('order_no')} product={p.get('product_name')}")
    if not found:
        print("  *** 未找到 WO-202605008 ***")
        print(f"  最近3条:")
        for p in rows2[:3]:
            print(f"    wo={p.get('order_no')} order={p.get('order_no')}")
except Exception as e:
    print(f"  失败: {e}")

# 3. 晨圣报工
print()
print("[晨圣报工 5008]")
try:
    r = requests.get('http://localhost:5008/api/schedule/list?t=1', timeout=10)
    data = r.json()
    items = data.get('data', data.get('items', []))
    found2 = [p for p in items if '202605008' in str(p.get('order_no',''))]
    print(f"  总{len(items)}条，含008: {len(found2)}条")
    for p in found2:
        print(f"  wo={p.get('order_no')} order={p.get('order_no')}")
    if not found2:
        print("  *** 未找到 WO-202605008 ***")
except Exception as e:
    print(f"  失败: {e}")

sys.stdout.close()
sys.stdout = sys.__stdout__
print("Done")
