import requests

# 1. 测试容器中心基础连通性
try:
    r = requests.get('http://127.0.0.1:5002/', timeout=5)
    print(f'GET / : HTTP {r.status_code}')
except Exception as e:
    print(f'GET / FAILED: {e}')

# 2. 测试容器中心 stats
try:
    r = requests.get('http://127.0.0.1:5002/container/api/stats', timeout=5)
    print(f'GET stats: HTTP {r.status_code}, {r.text[:200]}')
except Exception as e:
    print(f'GET stats FAILED: {e}')

# 3. 测试同步 - 无超时
try:
    r = requests.post('http://127.0.0.1:5002/api/enterprise/structure/sync', timeout=60)
    print(f'SYNC: HTTP {r.status_code}, body={r.text[:300]}')
except Exception as e:
    print(f'SYNC FAILED: {type(e).__name__}: {e}')
