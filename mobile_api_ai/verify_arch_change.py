"""验证方案A：调度中心统一云端通讯改造"""
import requests, json, os

RESULT_FILE = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\verify_result.json'
results = []

def save():
    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

def add(name, ok, detail):
    results.append({'test': name, 'ok': ok, 'detail': detail})
    save()

# 测试1: 容器中心不再调云端
try:
    r = requests.post('http://127.0.0.1:5002/api/enterprise/structure/sync',
                      json={'departments': [], 'users': []}, timeout=5)
    msg = r.json().get('message', '')
    add('容器中心不再主动调云端', r.status_code == 500 and '空' in msg, f'HTTP {r.status_code} msg={msg}')
except Exception as e:
    add('容器中心不再主动调云端', False, str(e))

# 测试2: 容器中心可接收调度中心推送
try:
    r = requests.post('http://127.0.0.1:5002/api/enterprise/structure/sync',
                      json={'departments': [{'id': 1, 'name': 'test', 'parentid': 0}], 'users': []}, timeout=5)
    d = r.json()
    add('容器中心接收推送正常', r.status_code == 200 and d.get('code') == 0, f'HTTP {r.status_code} code={d.get("code")}')
except Exception as e:
    add('容器中心接收推送正常', False, str(e))

# 测试3: 调度中心 force_cloud=1 直接调云端
try:
    r = requests.get('http://127.0.0.1:5003/api/dispatch-center/operators/wechat-departments?force_cloud=1', timeout=30)
    d = r.json()
    depts = d.get('data', {}).get('departments', [])
    add('调度中心直接调云端force_cloud=1', r.status_code == 200 and d.get('code') == 0 and len(depts) > 0,
        f'HTTP {r.status_code} code={d.get("code")} 部门数={len(depts)}')
except Exception as e:
    add('调度中心直接调云端force_cloud=1', False, str(e))

# 测试4: 调度中心 force_cloud=0 读容器中心缓存
try:
    r = requests.get('http://127.0.0.1:5003/api/dispatch-center/operators/wechat-departments', timeout=10)
    d = r.json()
    depts = d.get('data', {}).get('departments', [])
    add('调度中心读缓存force_cloud=0', r.status_code == 200 and d.get('code') == 0,
        f'HTTP {r.status_code} code={d.get("code")} 部门数={len(depts)}')
except Exception as e:
    add('调度中心读缓存force_cloud=0', False, str(e))

print('验证完成，结果已保存到 verify_result.json')
