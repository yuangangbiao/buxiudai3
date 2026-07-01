"""测试报工 API - 验证进度计算"""
import urllib.request
import json
import sys

BASE = 'http://localhost:5008'

def post(path, data):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(f'{BASE}{path}', data=body,
                                 headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode('utf-8'))

def get(path):
    resp = urllib.request.urlopen(f'{BASE}{path}')
    return json.loads(resp.read().decode('utf-8'))

if len(sys.argv) < 2:
    print("用法: python test_report.py <订单号>")
    print("示例: python test_report.py ORD-202604210003")
    sys.exit(1)

order_no = sys.argv[1]

print(f'=== 报工前信息: {order_no} ===')
info = get(f'/api/scan-info?code={order_no}')
data = info.get('data', {})
quantity = float(data.get('quantity', 0))
total_before = float(data.get('total_completed_qty', 0))
print(f'需求数: {quantity}')
print(f'总进度: {total_before}')

rates_before = []
for p in data.get('processes', []):
    cq = float(p.get('completed_qty', 0))
    rq = float(p.get('required_qty', 0))
    if cq > 0:
        rate = cq / rq if rq > 0 else 0
        rates_before.append(rate)
        print(f'  {p["process_name"]}: {cq}/{rq} ({rate*100:.1f}%)')

if rates_before:
    avg_before = sum(rates_before) / len(rates_before)
    expected_before = round(avg_before * quantity)
    ok = int(total_before) == expected_before
    print(f'\n平均完成率: {avg_before*100:.1f}%')
    print(f'预期总进度: {expected_before}')
    print(f'{"✅ 正确" if ok else "❌ 错误"}')
