"""直接测试 task_type='report' 的响应"""
import json, urllib.request, urllib.error

API_BASE = 'http://127.0.0.1:5002'
API_KEY = 'test-api-key-12345'

body = {
    'task_type': 'report',
    'title': 'test-report',
    'content': {
        'process_code': 'P07',
        'process_name': '编制右旋',
        'order_no': 'ORD-202604210002',
        'planned_qty': 20,
        'progress_type': 'daily_plan',
    },
    'operator_id': 'shengchan_test001',
    'priority': 'normal',
    'related_order': 'ORD-202604210002',
    'related_process': '编制右旋',
    'source': 'desktop_publish_test',
}
data = json.dumps(body).encode('utf-8')
req = urllib.request.Request(f'{API_BASE}/api/internal/publish', data=data,
    headers={'Content-Type': 'application/json', 'X-API-Key': API_KEY})
try:
    resp = urllib.request.urlopen(req, timeout=10)
    resp_data = json.loads(resp.read().decode('utf-8'))
    print("Response:", json.dumps(resp_data, ensure_ascii=False, indent=2))
except urllib.error.HTTPError as e:
    body = e.read().decode('utf-8')
    print(f"HTTPError {e.code}: {body}")
except Exception as e:
    print(f"Error: {e}")
