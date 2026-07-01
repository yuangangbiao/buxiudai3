import requests, json

r1 = requests.get('http://127.0.0.1:5003/api/dispatch-center/processes', params={'page':1,'size':20}, timeout=5)
print('5003 status:', r1.status_code)
if r1.status_code == 200:
    data = r1.json()
    procs = data.get('data', data.get('processes', data))
    items = []
    if isinstance(procs, list): items = procs
    elif isinstance(procs, dict): items = procs.get('items', procs.get('records', []))
    print('=== 调度中心 ===')
    for p in items:
        print('  %s | %s | %s' % (p.get('order_no','?'), p.get('product_name','?'), p.get('quantity','?')))
    print('Total: %d' % len(items))
else:
    print(r1.text[:200])

r2 = requests.get('http://127.0.0.1:5008/api/schedule/list', timeout=5)
print('\n5008 status:', r2.status_code)
if r2.status_code == 200:
    data2 = r2.json()
    items2 = data2.get('data', [])
    print('=== 晨圣报工 ===')
    for s in items2:
        wo = s.get('workOrderNo', s.get('order_no', '?'))
        pn = s.get('productName', s.get('product_name', '?'))
        qty = s.get('quantity', '?')
        print('  %s | %s | %s' % (wo, pn, qty))
    print('Total: %d' % len(items2))
else:
    print(r2.text[:200])
