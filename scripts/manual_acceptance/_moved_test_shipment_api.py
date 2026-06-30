import urllib.request, json, base64

# Generate fake token same as browser
user = {'id': 15, 'name': '测试', 'role': 'worker'}
token = base64.b64encode(f"{user['id']}:{user['name']}".encode('utf-8')).decode('ascii')
print('Fake token:', token[:30])

headers = {'X-Dispatch-Token': token}
base_url = 'http://localhost:5001/api'

apis = [
    ('/shipment/pending', 'GET'),
    ('/shipment/list', 'GET'),
    ('/shipment/tracking-list', 'GET'),
    ('/shipment/finished-goods', 'GET'),
]

for path, method in apis:
    url = f'{base_url}{path}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode('utf-8'))
            items = data.get('data') or []
            if isinstance(items, list):
                print(f'{method} {path}: code={data.get("code")}, items={len(items)}')
            else:
                print(f'{method} {path}: code={data.get("code")}, data_type={type(items).__name__}')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f'{method} {path}: HTTP {e.code} - {body[:100]}')
    except Exception as e:
        print(f'{method} {path}: ERROR {e}')

print('--- DONE ---')
