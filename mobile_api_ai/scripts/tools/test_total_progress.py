"""验证总进度按工序完成率取平均的算法"""
import urllib.request
import json
import sys

BASE = 'http://localhost:5008'

def get(path):
    url = BASE + path
    resp = urllib.request.urlopen(url)
    raw = resp.read().decode('utf-8')
    return json.loads(raw)

def test_order(order_no):
    data = get(f'/api/scan-info?code={order_no}').get('data', {})
    quantity = float(data.get('quantity', 0))
    total_completed = float(data.get('total_completed_qty', 0))

    print(f'\n订单: {order_no}')
    print(f'需求数: {quantity}')
    print(f'API 返回 total_completed_qty: {total_completed}')
    print(f'工序列表:')

    rates = []
    for p in data.get('processes', []):
        rq = float(p.get('required_qty', 0))
        cq = float(p.get('completed_qty', 0))
        rate = min(cq / rq, 1.0) if rq > 0 else 0
        rates.append(rate)
        print(f'  {p["process_name"]}: {cq}/{rq} ({rate*100:.1f}%)')

    if not rates:
        print('  (无工序数据，跳过验证)')
        return

    avg_rate = sum(rates) / len(rates)
    expected = round(avg_rate * quantity)
    actual = int(total_completed)

    print(f'\n平均完成率: {avg_rate*100:.1f}%')
    print(f'预期 total_completed_qty: {expected}')
    print(f'实际 total_completed_qty: {actual}')

    if actual == expected:
        print(f'✅ 总进度计算正确')
    else:
        print(f'❌ 总进度计算错误! 差值: {actual - expected}')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_order(sys.argv[1])
    else:
        print("用法: python test_total_progress.py <订单号>")
        print("示例: python test_total_progress.py ORD-202604210003")
