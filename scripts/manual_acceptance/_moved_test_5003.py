import urllib.request, json, base64

token = base64.b64encode("15:测试".encode('utf-8')).decode('ascii')
headers = {'X-Dispatch-Token': token}
order_no = 'ORD-202604210001'

for path in [f'/api/schedule/status/{order_no}', f'/api/schedule/history/{order_no}', '/api/schedule/list', '/api/schedule/']:
    url = f'http://localhost:5003{path}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode('utf-8'))
            print(f'=== 5003{path} ===')
            print(json.dumps(data, ensure_ascii=False, indent=2)[:800])
    except Exception as e:
        print(f'5003{path}: ERROR {e}')
