import urllib.request, json, base64

token = base64.b64encode("15:测试".encode('utf-8')).decode('ascii')
headers = {'X-Dispatch-Token': token}

for path in ['/api/production/list', '/api/schedule/list?status=已排产', '/api/schedule/pending', '/api/schedule/list?status=production']:
    url = f'http://localhost:5001{path}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode('utf-8'))
            items = data.get('data', [])
            if isinstance(items, list):
                print(f'{path}: code={data.get("code")}, list_len={len(items)}')
                if items:
                    print(f'  Sample keys: {list(items[0].keys()) if items else []}')
                    print(f'  First item: {json.dumps(items[0], ensure_ascii=False)[:200]}')
            else:
                print(f'{path}: code={data.get("code")}, data_type={type(items).__name__}')
    except Exception as e:
        print(f'{path}: ERROR {e}')
