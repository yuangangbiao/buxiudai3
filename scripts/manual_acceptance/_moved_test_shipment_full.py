import urllib.request, json, base64

token = base64.b64encode("15:测试".encode('utf-8')).decode('ascii')
headers = {'X-Dispatch-Token': token, 'Content-Type': 'application/json; charset=utf-8'}
base_url = 'http://localhost:5001/api'

# 1. Check existing orders
req = urllib.request.Request(f'{base_url}/orders/list?limit=5',
    headers={'X-Dispatch-Token': token})
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode('utf-8'))
orders = (data.get('data') or {}).get('orders') or []
print(f'Orders found: {len(orders)}')
for o in orders[:3]:
    print(f'  {o.get("order_no")} - {o.get("customer_name")} - {o.get("order_status")}')

# 2. Try creating a shipment with first order
if orders:
    order_no = orders[0].get('order_no')
    print(f'\nCreating shipment for order: {order_no}')
    create_data = json.dumps({'order_no': order_no, 'warehouse': '成品仓库'}).encode('utf-8')
    req = urllib.request.Request(f'{base_url}/shipment/create',
        data=create_data, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read().decode('utf-8'))
            print('Create result:', json.dumps(result, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f'HTTP {e.code}:', e.read().decode('utf-8')[:200])

# 3. Test shipment with invalid order
print('\nTest create with invalid order:')
create_data = json.dumps({'order_no': 'INVALID-NOT-EXIST-12345'}).encode('utf-8')
req = urllib.request.Request(f'{base_url}/shipment/create',
    data=create_data, headers=headers)
try:
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read().decode('utf-8'))
        print('Result:', json.dumps(result, ensure_ascii=False))
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}:', e.read().decode('utf-8')[:200])

print('\n--- DONE ---')
