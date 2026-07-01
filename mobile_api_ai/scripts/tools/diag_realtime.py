import sys
sys.stdout = open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\scripts\tools\diag_rt.txt', 'w', encoding='utf-8', buffering=1)
sys.stderr = sys.stdout

import sqlite3, requests, socket

print("=== 实时诊断 ===")

# 1. 当前端口状态
print("\n[1] 端口状态")
for port, name in [(5002, 'container_center'), (5003, 'wechat_server'), (5008, 'app')]:
    sock = socket.socket()
    sock.settimeout(2)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    print(f"  {port} ({name}): {'监听中' if result == 0 else f'断开({result})'}")

# 2. 立即发送一个测试工单
print("\n[2] 立即发送测试工单 WO-REAL-TIME")
try:
    r = requests.post(
        'http://localhost:5002/api/schedule/publish',
        json={
            'order_no': 'WO-REAL-TIME',
            'order_no': 'ORD-REAL-TIME',
            'product_name': '实时测试',
            'quantity': 1,
            'unit': '件',
        },
        timeout=10
    )
    data = r.json()
    print(f"  status={r.status_code} code={data.get('code')} msg={data.get('message')}")
    if data.get('code') == 0:
        print("  ✅ 发送成功")
    else:
        print(f"  ❌ 发送失败: {data}")
except Exception as e:
    print(f"  ❌ 发送失败: {e}")

# 3. 验证是否写入数据库
print("\n[3] 验证数据库")
db = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT id, order_no, created_at FROM process_records WHERE order_no='WO-REAL-TIME'")
rows = c.fetchall()
print(f"  数据库中找到 {len(rows)} 条")
conn.close()

# 4. 检查调度中心是否显示
print("\n[4] 验证调度中心")
try:
    r = requests.get('http://localhost:5003/api/dispatch-center/processes?t=1', timeout=10)
    data = r.json()
    found = [p for p in data.get('data', []) if 'REAL-TIME' in str(p.get('order_no',''))]
    print(f"  调度中心找到 {len(found)} 条")
except Exception as e:
    print(f"  失败: {e}")

print("\n=== 测试完成 ===")

sys.stdout.close()
sys.stdout = sys.__stdout__
print("Done")
