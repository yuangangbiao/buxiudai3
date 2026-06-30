#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib.request, json
url = 'http://127.0.0.1:5002/api/v4/work_order?page=1&size=20'
r = urllib.request.urlopen(url, timeout=5)
d = json.loads(r.read().decode('utf-8'))
items = d.get('items', [])
print(f'5002 work_order 总数: {len(items)}')
print()
for it in items[:8]:
    s = it.get('status', '')
    sc = it.get('status_code', '-')
    dt = it.get('data_type', '')
    p = it.get('priority', '')
    title = it.get('title', '')[:30]
    print(f"  status={s!r:10s} status_code={sc!r:15s} data_type={dt!r:15s} priority={p!r:10s} title={title!r}")
