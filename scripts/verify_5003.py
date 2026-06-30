#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib.request, json
for o in ['ORD-202604210004','ORD-202605020001','ORD-202604210002','ORD-202605010001']:
    url = f'http://127.0.0.1:5003/api/dispatch-center/workorder/{o}'
    r = urllib.request.urlopen(url, timeout=5)
    d = json.loads(r.read().decode('utf-8'))
    inner = d.get('data', {})
    print(f'=== {o} ===')
    for k in ('process_tasks','flow_steps','flow_production','material_tasks','quality_tasks'):
        items = inner.get(k) or []
        print(f'  {k}: {len(items)}')
    s = inner.get('stats', {})
    print(f'  stats: {s}')
