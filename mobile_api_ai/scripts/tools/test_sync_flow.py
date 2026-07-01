"""测试容器中心从云端同步企业架构的全流程"""
import requests
import json
import sys

BASE_URL = 'http://localhost:5002'
SYNC_URL = f'{BASE_URL}/api/enterprise/structure/sync'
CACHE_URL = f'{BASE_URL}/api/enterprise/structure'

def log(msg):
    print(msg)

def test_sync():
    log('=== 测试1: 容器中心从云端同步企业架构 ===')
    log(f'POST {SYNC_URL}')
    resp = requests.post(SYNC_URL, timeout=30)
    log(f'HTTP {resp.status_code}')
    data = resp.json()
    log(f'code={data.get("code")}, message={data.get("message","")}')

    if data.get('code') != 0:
        log(f'ERROR: {json.dumps(data, ensure_ascii=False, indent=2)[:1000]}')
        return False

    synced = data.get('data', {})
    depts = synced.get('departments', [])
    users = synced.get('users', [])
    log(f'Departments: {len(depts)}')
    log(f'Users: {len(users)}')
    for d in depts[:5]:
        log(f'  - {d.get("name")} (id={d.get("id")})')
    log(f'Updated at: {synced.get("updated_at", "?")}')
    return True

def test_cache():
    log('\n=== 测试2: 从容器中心读取缓存(验证已存入数据库) ===')
    log(f'GET {CACHE_URL}')
    resp = requests.get(CACHE_URL, timeout=10)
    data = resp.json()
    log(f'HTTP {resp.status_code}, code={data.get("code")}')

    cached = data.get('data', {})
    depts = cached.get('departments', [])
    users = cached.get('users', [])
    log(f'Departments(DB): {len(depts)}')
    log(f'Users(DB): {len(users)}')
    log(f'Updated at: {cached.get("updated_at", "?")}')

    if depts:
        log('Cache read SUCCESS - data persisted in database')
        return True
    else:
        log('WARNING: Cache empty, data not persisted in database')
        return False

def test_dispatch_sync():
    log('\n=== 测试3: 调度中心通过容器中心同步(force_cloud=1) ===')
    dispatch_url = 'http://localhost:5003/api/dispatch-center/operators/wechat-departments?force_cloud=1'
    log(f'GET {dispatch_url}')
    try:
        resp = requests.get(dispatch_url, timeout=35)
        data = resp.json()
        log(f'HTTP {resp.status_code}, code={data.get("code")}')

        if data.get('code') != 0:
            log(f'ERROR: {data.get("message")}')
            return False

        dd = data.get('data', {})
        log(f'source={dd.get("source","?")}')
        log(f'flat_count={dd.get("flat_count")}')
        depts = dd.get('departments', [])
        log(f'root_depts={len(depts)}')
        for dept in depts:
            log(f'  - {dept.get("name")} (members={len(dept.get("members",[]))})')
            for child in dept.get('children', []):
                log(f'      - {child.get("name")} (members={len(child.get("members",[]))})')
        return True
    except requests.exceptions.ConnectionError:
        log('SKIP: 调度中心未启动(端口5003)')
        return None

if __name__ == '__main__':
    ok = test_sync()
    if ok:
        test_cache()
    test_dispatch_sync()
    log('\n=== DONE ===')
