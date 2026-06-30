"""重启 5008 验证 token 颁发"""
import subprocess
import time
import requests
import os
import signal

PY = r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe'
APP = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\app.py'
CWD = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'

# 杀旧 5008
for line in subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout.split('\n'):
    if ':5008' in line and 'LISTENING' in line:
        pid = line.split()[-1]
        subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True, text=True)
        print(f'killed {pid}')

time.sleep(3)

# 启动新 5008
proc = subprocess.Popen(
    [PY, APP],
    cwd=CWD,
    creationflags=subprocess.CREATE_NEW_CONSOLE
)
print(f'started PID {proc.pid}')

# 等待
for i in range(15):
    time.sleep(1)
    try:
        r = requests.post('http://127.0.0.1:5008/api/login',
                          json={'username': '微风细雨'}, timeout=3)
        data = r.json().get('data', {})
        token = data.get('token', '')
        if token:
            print(f'✅ 5008 启动成功 (i={i}s)')
            print(f'   token: {token[:60]}...')
            print(f'   user_id: {data.get("user_id", "NONE")}')

            # 用 token 鉴权测试
            r2 = requests.post(
                'http://127.0.0.1:5008/api/attendance',
                headers={'Authorization': f'Bearer {token}'},
                json={'action': 'check-in'},
                timeout=5,
            )
            print(f'   用 token 调 attendance: HTTP {r2.status_code}')

            r3 = requests.get(
                'http://127.0.0.1:5008/api/process/my-tasks',
                headers={'Authorization': f'Bearer {token}'},
                timeout=5,
            )
            print(f'   用 token 调 my-tasks: HTTP {r3.status_code} {r3.text[:100]}')
            break
    except Exception as e:
        if i < 14:
            continue
        print(f'启动超时: {e}')
