import urllib.request, json

url = 'http://127.0.0.1:8008/api/sync/sub-step-report'
data = json.dumps({
    'order_no': 'ORD-202604210002',
    'step_name': '编制右旋',
    'process_code': 'P07',
    'quantity': 10,
    'operator': '苑岗彪'
}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    resp = urllib.request.urlopen(req, timeout=5)
    print(f'Status: {resp.status}')
    print(f'Body: {resp.read().decode("utf-8")}')
except urllib.error.HTTPError as e:
    print(f'HTTP Status: {e.code}')
    body = e.read().decode('utf-8')
    print(f'Body: {body}')
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
