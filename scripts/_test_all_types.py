"""测试所有三种 task_type 的 API 响应"""
import json, urllib.request, urllib.error

API_BASE = 'http://127.0.0.1:5002'
API_KEY = 'test-api-key-12345'

def test_publish(task_type, title, content, operator):
    body = {
        'task_type': task_type,
        'title': title,
        'content': content,
        'operator_id': operator,
        'priority': 'normal',
        'related_order': f'ORD-E2E-TEST',
        'related_process': '测试工序',
        'source': 'desktop_publish_test',
    }
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(f'{API_BASE}/api/internal/publish', data=data,
        headers={'Content-Type': 'application/json', 'X-API-Key': API_KEY})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        resp_data = json.loads(resp.read().decode('utf-8'))
        return resp_data, 200
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode('utf-8')), e.code
    except Exception as e:
        return {'error': str(e)}, 0

print("=== 测试 report ===")
resp, status = test_publish('report', 'test-report', {'process_name': '测试工序', 'process_code': 'P99', 'order_no': 'ORD-E2E-TEST', 'planned_qty': 20}, 'shengchan_direct')
print(f"Status: {status}")
print(f"Response: {json.dumps(resp, ensure_ascii=False, indent=2)}")

print("\n=== 测试 quality ===")
resp, status = test_publish('quality', 'test-quality', {'process_name': '质检工序', 'order_no': 'ORD-E2E-TEST', 'inspection_type': 'process_inspection'}, 'zhijian_direct')
print(f"Status: {status}")
print(f"Response: {json.dumps(resp, ensure_ascii=False, indent=2)}")

print("\n=== 测试 material ===")
resp, status = test_publish('material', 'test-material', {'material': '钢材', 'order_no': 'ORD-E2E-TEST', 'quantity': 10}, 'wuliao_direct')
print(f"Status: {status}")
print(f"Response: {json.dumps(resp, ensure_ascii=False, indent=2)}")
