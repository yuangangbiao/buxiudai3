import requests

token = '9eb42d04991c76c6e2ea0483ab5e8026'

# 测试 GitHub
print('=== 测试 GitHub ===')
r = requests.get(
    'https://api.github.com/user',
    headers={'Authorization': f'token {token}'},
    timeout=15
)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    user = r.json()
    print(f'GitHub用户: {user.get("login")}')
else:
    print(f'GitHub失败: {r.text[:200]}')

# 测试 Gitee
print()
print('=== 测试 Gitee ===')
r2 = requests.get(
    'https://gitee.com/api/v5/user',
    params={'access_token': token},
    timeout=15
)
print(f'Status: {r2.status_code}')
if r2.status_code == 200:
    user = r2.json()
    print(f'Gitee用户: {user.get("login")}')