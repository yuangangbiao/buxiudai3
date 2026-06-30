import urllib.request, json, base64

token = base64.b64encode("15:测试".encode('utf-8')).decode('ascii')
headers = {'X-Dispatch-Token': token}

for path in ['/api/orders/list', '/api/dispatch-center/order-status-list']:
    url = f'http://localhost:5001{path}'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode('utf-8'))
        items = (data.get('data') or {}).get('orders') or []
        print(f'{path}: total={data.get("data",{}).get("total")}, items={len(items)}')
        for o in items[:3]:
            print(f'  id={o.get("id")} order_no={o.get("order_no")} customer={o.get("customer_name")}')
