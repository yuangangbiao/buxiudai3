"""直接诊断 - 模拟 sync_operators_from_wechat 完整调用流程"""
import os, sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.chdir(os.path.join(os.path.dirname(__file__), 'mobile_api_ai'))
sys.path.insert(0, os.getcwd())

print("=" * 60)
print("STEP 1: load cloud_config")
cfg_file = 'cloud_config.json'
if not os.path.exists(cfg_file):
    print("FAIL: cloud_config.json not exist")
    sys.exit(1)
with open(cfg_file, 'r', encoding='utf-8') as f:
    cfg = json.load(f)
os.environ['WECHAT_CLOUD_HOST'] = cfg['cloud_host']
os.environ['WECHAT_CLOUD_API_KEY'] = cfg['api_key']
print(f"OK: host={cfg['cloud_host']}, api_key={cfg['api_key'][:8]}...")

print()
print("=" * 60)
print("STEP 2: call cloud /api/wechat/users")
import requests
import time
t0 = time.time()
try:
    resp = requests.get(f"{cfg['cloud_host']}/api/wechat/users",
                        headers={'X-API-Key': cfg['api_key']}, timeout=60)
    t1 = time.time()
    print(f"  cost: {t1-t0:.1f}s, HTTP {resp.status_code}")
    if resp.status_code != 200:
        print(f"FAIL: cloud return {resp.status_code}: {resp.text[:200]}")
        sys.exit(1)
    data = resp.json()
    if data.get('code') != 0:
        print(f"FAIL: cloud biz error: {data.get('message')}")
        sys.exit(1)
    print(f"OK: users={len(data.get('users',[]))}, depts={len(data.get('departments',[]))}")
except Exception as e:
    print(f"FAIL: cloud request exception: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("STEP 3: test write to container_config")
from container_config import container_config, OperatorConfig
ops_before = len(container_config.get_all_operators())
print(f"  operators before: {ops_before}")

wechat_users = data.get('users', [])
departments = {d.get('id'): d.get('name', '') for d in data.get('departments', [])}

deduped = {}
for user in wechat_users:
    userid = user.get('userid', '')
    if not userid:
        continue
    if userid not in deduped:
        deduped[userid] = {**user, '_dept_names': set()}
    for did in user.get('department', []):
        deduped[userid]['_dept_names'].add(departments.get(did, str(did)))

print(f"  deduped: {len(deduped)} persons")

# test first 5
added = 0; updated = 0; errors = []
existing_ops = {op.id: op for op in container_config.get_all_operators()}

for userid, user in list(deduped.items())[:5]:
    name = user.get('name', '')
    dept_name = '/'.join(sorted(user['_dept_names'])) if user['_dept_names'] else ''
    if not name: continue
    operator_id = userid
    try:
        if operator_id in existing_ops:
            container_config.update_operator(operator_id,
                name=name, department=dept_name, role='employee', wechat_userid=userid)
            updated += 1
            print(f"  UPDATE: {operator_id} -> {name}")
        else:
            op = OperatorConfig(id=operator_id, name=name, role='employee',
                department=dept_name, enabled=True, notify_enabled=True,
                max_tasks=10, wechat_userid=userid)
            if container_config.add_operator(op):
                added += 1
                print(f"  ADD: {operator_id} -> {name}")
            else:
                errors.append(f"add_operator returned False: {operator_id}")
    except Exception as e:
        errors.append(f"{operator_id}: {e}")
        print(f"  EXCEPTION: {operator_id} -> {e}")

print(f"  added={added}, updated={updated}")
if errors:
    print(f"  ERRORS: {errors}")
else:
    print("  OK: no write errors")

# test full sync
print()
print("=" * 60)
print("STEP 4: full sync all {len(deduped)} persons")
added = 0; updated = 0; errors = []
existing_ops = {op.id: op for op in container_config.get_all_operators()}

for userid, user in deduped.items():
    name = user.get('name', '')
    dept_name = '/'.join(sorted(user['_dept_names'])) if user['_dept_names'] else ''
    if not name: continue
    operator_id = userid
    try:
        if operator_id in existing_ops:
            container_config.update_operator(operator_id,
                name=name, department=dept_name, role='employee', wechat_userid=userid)
            updated += 1
        else:
            op = OperatorConfig(id=operator_id, name=name, role='employee',
                department=dept_name, enabled=True, notify_enabled=True,
                max_tasks=10, wechat_userid=userid)
            if container_config.add_operator(op):
                added += 1
            else:
                errors.append(f"add_operator False: {operator_id}")
    except Exception as e:
        errors.append(f"{operator_id}: {e}")

print(f"  added={added}, updated={updated}")
if errors:
    print(f"  ERRORS count: {len(errors)}")
    for e in errors[:5]: print(f"    {e}")
else:
    print("  OK: all success")

ops_after = len(container_config.get_all_operators())
print(f"  operators count: {ops_before} -> {ops_after}")
