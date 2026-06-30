#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib.request, json
url = 'http://127.0.0.1:5003/api/dispatch-center/workorder/ORD-202605010001'
r = urllib.request.urlopen(url, timeout=5)
d = json.loads(r.read().decode('utf-8'))
inner = d.get('data', {})

print(f"=== {inner.get('order_no')} status 中文验证 ===")
print(f"  order.status: {inner.get('status')!r}")
print()

print("=== process_tasks[0:3] ===")
for t in inner.get('process_tasks', [])[:3]:
    print(f"  status={t.get('status')!r:12s} status_code={t.get('status_code', '-')!r:12s} data_type={t.get('data_type')!r:12s} related_process={t.get('related_process')!r}")
print()

print("=== flow_steps[0:3] ===")
for t in inner.get('flow_steps', [])[:3]:
    print(f"  status={t.get('status')!r:12s} status_code={t.get('status_code', '-')!r:12s} data_type={t.get('data_type')!r:12s} related_process={t.get('related_process')!r}")
print()

print("=== material_tasks[0:2] ===")
for t in inner.get('material_tasks', [])[:2]:
    print(f"  status={t.get('status')!r:12s} status_code={t.get('status_code', '-')!r:12s} data_type={t.get('data_type')!r:12s} related_process={t.get('related_process')!r}")
print()

print("=== quality_tasks ===")
for t in inner.get('quality_tasks', []):
    print(f"  status={t.get('status')!r:12s} status_code={t.get('status_code', '-')!r:12s} data_type={t.get('data_type')!r:12s} related_process={t.get('related_process')!r}")
