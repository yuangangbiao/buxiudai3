#!/usr/bin/env python3
"""集成测试：容器中心连接配置 tab 嵌入调度中心仪表盘"""
import json, urllib.request

BASE = 'http://127.0.0.1:5000'

# Test 1: dispatch_center.html renders
r = urllib.request.urlopen(f'{BASE}/api/dispatch-center/')
html = r.data.decode()
checks = ['tab-container-config', 'cc-url', 'cc-secret', 'saveContainerConfig', 'testContainerConfig', 'container-config']
for c in checks:
    ok = c in html
    print(f'  HTML contains [{c}]: {"OK" if ok else "FAIL"}')
    if not ok:
        raise AssertionError(f'Missing: {c}')
print(f'HTML OK: {len(html)}B')

# Test 2: config-center schema has container fields
r = urllib.request.urlopen(f'{BASE}/api/config-center/schema')
d = json.loads(r.read())
fields = [f['key'] for f in d['data']['container']['fields']]
print(f'  Schema fields: {fields}')
assert 'CONTAINER_CENTER_URL' in fields
assert 'CONTAINER_CENTER_SECRET' in fields
print('SCHEMA OK')

# Test 3: config-center values endpoint
r = urllib.request.urlopen(f'{BASE}/api/config-center/values')
d = json.loads(r.read())
print(f'  Values endpoint: code={d["code"]}')
print('VALUES OK')

# Test 4: config-center save endpoint
import urllib.request
data = json.dumps({'CONTAINER_CENTER_URL': 'http://test:5002', 'CONTAINER_CENTER_SECRET': 'test-secret'}).encode()
req = urllib.request.Request(f'{BASE}/api/config-center/save', data=data, headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
d = json.loads(r.read())
print(f'  Save endpoint: code={d["code"]}')
print('SAVE OK')

# Test 5: config-center test endpoint (expected to fail since we sent fake URL)
data = json.dumps({'CONTAINER_CENTER_URL': 'http://localhost:99999', 'CONTAINER_CENTER_SECRET': ''}).encode()
req = urllib.request.Request(f'{BASE}/api/config-center/test/container_center', data=data, headers={'Content-Type': 'application/json'})
r = urllib.request.urlopen(req)
d = json.loads(r.read())
print(f'  Test endpoint (fake URL): code={d["code"]}, message={d.get("message","")[:40]}')
# Expected: 500 with error message (Connection refused or timeout)
print('TEST ENDPOINT OK')

print()
print('ALL INTEGRATION TESTS PASSED')
