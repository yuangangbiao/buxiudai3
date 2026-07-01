# -*- coding: utf-8 -*-
import urllib.request, json

BASE = 'http://localhost:5003/api/dispatch-center'

# Check current process state
print("=== 检查流程状态 ===")
req = urllib.request.Request(BASE + '/processes?status=scheduled')
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read().decode('utf-8'))
for p in data.get('data', []):
    if p.get('order_no') == 'WO-202605004':
        print(json.dumps(p, ensure_ascii=False, indent=2))
        break
