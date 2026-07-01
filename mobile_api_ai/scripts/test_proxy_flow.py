import requests, json, sys

WC = 'http://localhost:5006'
CC = 'http://localhost:5002'
API_KEY = 'dev-local-cloud-api-key'
HEADERS = {'X-API-Key': API_KEY, 'Content-Type': 'application/json'}


def test_get_empty():
    print('=== 1. GET 空缓存 ===')
    r = requests.get(f'{WC}/cloud/org/enterprise_structure', headers=HEADERS, timeout=5)
    print(f'  -> {r.status_code}', json.dumps(r.json(), ensure_ascii=False)[:200])


def test_post():
    print('=== 2. POST 发送企业架构 ===')
    data = {
        'departments': [
            {'id': 1, 'name': '公司总部', 'parentid': 0, 'order': 1},
            {'id': 2, 'name': '生产部', 'parentid': 1, 'order': 2},
            {'id': 3, 'name': '销售部', 'parentid': 1, 'order': 3},
        ],
        'users': [
            {'userid': 'zhangsan', 'name': '张三', 'department': [2]},
            {'userid': 'lisi', 'name': '李四', 'department': [3]},
        ]
    }
    r = requests.post(f'{WC}/cloud/org/enterprise_structure', json=data, headers=HEADERS, timeout=5)
    j = r.json()
    print(f'  -> {r.status_code}', json.dumps(j, ensure_ascii=False)[:200])
    return j.get('code') == 0


def test_get_cached():
    print('=== 3. GET 有缓存 ===')
    r = requests.get(f'{WC}/cloud/org/enterprise_structure', headers=HEADERS, timeout=5)
    j = r.json()
    if j.get('code') == 0:
        d = j.get('data', {})
        print(f'  -> code={j["code"]}, depts={len(d.get("departments", []))}, users={len(d.get("users", []))}')
    else:
        print(f'  -> {json.dumps(j, ensure_ascii=False)[:200]}')


def test_cc_verify():
    print('=== 4. 容器中心验证 ===')
    r = requests.get(f'{CC}/api/enterprise/structure', timeout=5)
    j = r.json()
    d = j.get('data', {})
    print(f'  -> code={j["code"]}, depts={len(d.get("departments", []))}, users={len(d.get("users", []))}')


if __name__ == '__main__':
    test_get_empty()
    ok = test_post()
    if ok:
        test_get_cached()
        test_cc_verify()
    else:
        print('POST failed, skipping verification')
    print('\n=== 验证完成 ===')
    sys.exit(0)
