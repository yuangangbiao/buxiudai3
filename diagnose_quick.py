import os, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.chdir(os.path.join(os.path.dirname(__file__), 'mobile_api_ai'))
sys.path.insert(0, os.getcwd())

import requests, time
with open('cloud_config.json', encoding='utf-8') as f:
    cfg = json.load(f)

print('TEST1: cloud api')
t0 = time.time()
r = requests.get(cfg['cloud_host'] + '/api/wechat/users',
    headers={'X-API-Key': cfg['api_key']}, timeout=30)
print(f'HTTP {r.status_code} cost={time.time()-t0:.1f}s')

if r.status_code == 200:
    d = r.json()
    print(f'users={len(d.get("users",[]))} depts={len(d.get("departments",[]))}')
    if d.get('code') == 0:
        us = d['users']
        print(f'sample user: {json.dumps(us[0], ensure_ascii=False)[:200]}')
        print(f'sample dept: {json.dumps(d["departments"][0], ensure_ascii=False)[:200]}')

print('TEST2: container_config write')
from container_config import container_config, OperatorConfig
before = len(container_config.get_all_operators())
op = OperatorConfig(id='test_diag', name='test_diag', role='test')
result = container_config.add_operator(op)
print(f'add_operator result={result}')
container_config.remove_operator('test_diag')
print(f'operators before={before} after={len(container_config.get_all_operators())}')

print('ALL OK')
