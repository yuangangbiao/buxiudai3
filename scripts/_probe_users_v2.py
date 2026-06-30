"""用 name 字段测试 5001/5003 登录"""
import requests

# 5001 → 5003 代理，5001 用 username 字段
# 5003 用 name 字段匹配 operators.name
# 真实 name: 微风细雨 / 边疆 / 晨圣五金～客服 / 春天的雨 / 开心快乐 / 小曦

for name in ['微风细雨', '边疆', '春天的雨', '开心快乐', '小曦', '小圣', '小贺', '小钰']:
    r = requests.post('http://127.0.0.1:5003/api/login',
                      json={'username': name}, timeout=5)
    data = r.json()
    if data.get('code') == 0:
        user = data['data']
        print(f'  ✅ {name:12s} role={user.get("role","?"):8s} dept={user.get("department","?")[:30]}')
    else:
        print(f'  ❌ {name:12s} {data.get("message","?")[:50]}')

# 测试 '测试' 兜底
r = requests.post('http://127.0.0.1:5003/api/login', json={'username': '测试'}, timeout=5)
print(f'\n  测试兜底: code={r.json().get("code")} data={r.json().get("data",{})}')

# 也试 5008 mobile login
print('\n=== 5008 mobile login ===')
for name in ['微风细雨', '边疆', '测试', 'admin']:
    r = requests.post('http://127.0.0.1:5008/api/login', json={'username': name}, timeout=5)
    print(f'  {name:10s}: {r.status_code} {r.json()}')
