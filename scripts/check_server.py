import requests
import sys

BASE = 'http://localhost:5002'
ENDPOINTS = [
    ('/api/pool/status', '池状态'),
    ('/inventory/api/inventory', '库存列表'),
    ('/api/tasks', '任务列表'),
]

def check():
    all_ok = True
    for path, name in ENDPOINTS:
        url = f'{BASE}{path}'
        try:
            r = requests.get(url, timeout=5)
            ok = r.status_code == 200
            flag = 'OK' if ok else '异常'
            print(f'[{flag}] {name}')
            if not ok:
                print(f'  状态码: {r.status_code} 响应: {r.text[:200]}')
                all_ok = False
            else:
                print(f'  响应: {r.text[:150]}')
        except requests.ConnectionError:
            print(f'[失败] {name} - 无法连接')
            all_ok = False
        except Exception as e:
            print(f'[错误] {name} - {e}')
            all_ok = False
    return all_ok

print('='*40)
print('容器中心服务器健康检查')
print('='*40)
ok = check()
print()
print('结论:', '全部正常' if ok else '存在异常')
print('='*40)

if __name__ == '__main__':
    check()
