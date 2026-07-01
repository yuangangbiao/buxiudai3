import requests, json

print("=== 测试 container_center 5002 /api/schedule/publish 接口 ===")
print()

# 1. 检查接口是否正常响应
print("[1] 检查接口健康状态")
try:
    r = requests.get('http://localhost:5002/api/health', timeout=5)
    print(f"  /api/health 返回: {r.status_code}")
    try:
        print(f"  内容: {r.json()}")
    except Exception as e:
        print(f"  文本: {r.text[:200]} (JSON解析失败: {e})")
except Exception as e:
    print(f"  失败: {e}")

print()

# 2. 检查最近的排产记录（调试用，查看WO-202605007是否已到）
print("[2] 检查 container_center 5002 /api/schedule/publish 是否收到 WO-202605007")
try:
    r = requests.post(
        'http://localhost:5002/api/schedule/publish',
        json={
            'order_no': 'WO-TEST-VERIFY',
            'order_no': 'ORD-TEST-VERIFY',
            'product_name': '测试验证',
            'quantity': 100,
            'unit': '件',
            'plan_start': '2026-05-21',
            'plan_end': '2026-05-30',
            'customer_name': '测试客户',
            'notes': '诊断测试'
        },
        timeout=10
    )
    print(f"  POST /api/schedule/publish 返回:")
    print(f"    status: {r.status_code}")
    try:
        data = r.json()
        print(f"    code: {data.get('code')}")
        print(f"    message: {data.get('message')}")
        print(f"    full: {json.dumps(data, ensure_ascii=False)[:500]}")
    except Exception as e:
        print(f"    text: {r.text[:500]} (JSON解析失败: {e})")
except Exception as e:
    print(f"  失败: {e}")

print()

# 3. 检查 process_records 是否写入了测试记录
print("[3] 验证测试记录是否写入")
import sqlite3, os
db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
if os.path.exists(db):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("""
        SELECT id, order_no, order_no, product_name, created_at
        FROM process_records
        WHERE order_no = 'WO-TEST-VERIFY'
           OR order_no = 'ORD-TEST-VERIFY'
    """)
    rows = c.fetchall()
    if rows:
        print(f"  找到 {len(rows)} 条测试记录:")
        for r in rows:
            print(f"    wo={r[1]}  order={r[2]}  product={r[3]}  created={r[4]}")
    else:
        print("  未找到测试记录 - POST 可能未成功写入")
    conn.close()
