import requests, json

# 验证调度中心
r1 = requests.get('http://127.0.0.1:5003/api/dispatch-center/processes', params={'page':1,'size':20}, timeout=5)
if r1.status_code == 200:
    data = r1.json()
    procs = data.get('data', data.get('processes', data))
    items = []
    if isinstance(procs, list): items = procs
    elif isinstance(procs, dict): items = procs.get('items', procs.get('records', []))
    print('=== 调度中心 /processes ===')
    for p in items:
        wo = p.get('order_no', '?')
        od = p.get('order_no', '?')
        pn = p.get('product_name', '?')
        qty = p.get('quantity', '?')
        st = p.get('status', '?')
        print('  %s | %s | %s | %s | %s' % (wo, od, pn, qty, st))
    print('Total: %d' % len(items))
else:
    print('5003 Error: %d' % r1.status_code)

# 验证晨圣报工
r2 = requests.get('http://127.0.0.1:5008/api/schedule/list', timeout=5)
if r2.status_code == 200:
    data2 = r2.json()
    items2 = data2.get('data', [])
    print()
    print('=== 晨圣报工 /schedule/list ===')
    for s in items2:
        wo = s.get('workOrderNo', s.get('order_no', '?'))
        od = s.get('orderNo', s.get('order_no', '?'))
        pn = s.get('productName', s.get('product_name', '?'))
        qty = s.get('quantity', '?')
        st = s.get('status', '?')
        print('  %s | %s | %s | %s | %s' % (wo, od, pn, qty, st))
    print('Total: %d' % len(items2))
else:
    print('5008 Error: %d' % r2.status_code)
