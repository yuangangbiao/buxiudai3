"""诊断 report task_type 的问题"""
import json, urllib.request, urllib.error

API_BASE = 'http://127.0.0.1:5002'
API_KEY = 'test-api-key-12345'

body = {
    'task_type': 'report',
    'title': 'test-report-direct',
    'content': {
        'process_code': 'P99',
        'process_name': '测试工序',
        'order_no': 'ORD-0621020245',
        'planned_qty': 20,
    },
    'operator_id': 'shengchan_diag',
    'priority': 'normal',
    'related_order': 'ORD-0621020245',
    'related_process': '测试工序',
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
    body_e = e.read().decode('utf-8')
    print(f"HTTPError {e.code}: {body_e}")
except Exception as e:
    print(f"Error: {e}")
