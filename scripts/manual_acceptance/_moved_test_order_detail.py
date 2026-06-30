import urllib.request, json, base64

token = base64.b64encode("15:测试".encode('utf-8')).decode('ascii')
headers = {'X-Dispatch-Token': token}

for path in ['/api/orders/52/detail', '/api/orders/52/print', '/api/orders/52', '/api/dispatch-center/orders/52', '/api/dispatch-center/processes/52']:
    url = f'http://localhost:5001{path}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            content = r.read().decode('utf-8')[:200]
            print(f'{path}: {content[:200]}')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')[:200]
        print(f'{path}: HTTP {e.code} - {body[:200]}')
    except Exception as e:
        print(f'{path}: ERROR {e}')
