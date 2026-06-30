import urllib.request, json, base64

token = base64.b64encode("15:测试".encode('utf-8')).decode('ascii')
headers = {'X-Dispatch-Token': token}

# Try different API paths
apis = [
    'http://localhost:5003/api/dispatch-center/schedule/list',
    'http://localhost:5003/api/dispatch-center/schedule/pending',
    'http://localhost:5003/api/dispatch-center/schedule/status/ORD-202605020001',
    'http://localhost:5001/api/process/list',
    'http://localhost:5001/api/process/status/ORD-202605020001',
]

for url in apis:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read().decode('utf-8'))
            print(f'{url}')
            print(f'  code={data.get("code")} msg={data.get("message","")[:50]}')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')[:100]
        print(f'{url}: HTTP {e.code} - {body}')
    except Exception as e:
        print(f'{url}: ERROR {e}')
