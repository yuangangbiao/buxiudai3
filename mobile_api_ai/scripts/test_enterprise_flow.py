import requests, json, sys

BASE_CC = 'http://localhost:5002'  # 容器中心
BASE_DC = 'http://localhost:5003'  # 调度中心
BASE_WC = 'http://localhost:5006'  # 微信云端

def test_cc():
    print('=== 1. 容器中心 API ===')
    # GET 空缓存
    r = requests.get(f'{BASE_CC}/api/enterprise/structure', timeout=5)
    print(f'GET /api/enterprise/structure -> {r.status_code}', json.dumps(r.json(), ensure_ascii=False)[:200])

    # POST 保存
    data = {
        'departments': [
            {'id': 1, 'name': '公司总部', 'parentid': 0, 'order': 1},
            {'id': 2, 'name': '生产部', 'parentid': 1, 'order': 2},
        ],
        'users': [
            {'userid': 'zhangsan', 'name': '张三', 'department': [2]},
        ]
    }
    r = requests.post(f'{BASE_CC}/api/enterprise/structure', json=data, timeout=5)
    print(f'POST /api/enterprise/structure -> {r.status_code}', json.dumps(r.json(), ensure_ascii=False)[:200])

    # GET 有缓存
    r = requests.get(f'{BASE_CC}/api/enterprise/structure', timeout=5)
    j = r.json()
    depts = len(j.get('data', {}).get('departments', []))
    users = len(j.get('data', {}).get('users', []))
    print(f'GET /api/enterprise/structure (cached) -> {r.status_code}, depts={depts}, users={users}')

def test_dc():
    print('\n=== 2. 调度中心 webhook ===')
    try:
        r = requests.post(f'{BASE_DC}/api/enterprise/structure/push', json={'source': 'container_center', 'type': 'enterprise_structure_updated'}, timeout=5)
        print(f'webhook -> {r.status_code}', json.dumps(r.json(), ensure_ascii=False)[:200])
    except requests.ConnectionError:
        print(f'webhook -> FAIL (5003 未运行)')

def test_wc():
    print('\n=== 3. 微信云端代理 ===')
    try:
        r = requests.get(f'{BASE_WC}/cloud/org/enterprise_structure', timeout=5)
        print(f'GET /cloud/org/enterprise_structure -> {r.status_code}', json.dumps(r.json(), ensure_ascii=False)[:300])
    except requests.ConnectionError:
        print(f'/cloud/org/enterprise_structure -> FAIL (5006 未运行)')

if __name__ == '__main__':
    test_cc()
    test_dc()
    test_wc()
    print('\n=== 验证完成 ===')
    sys.exit(0)
