"""完整杀 5008 + 重启"""
import subprocess
import time
import requests

PY = r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe'
APP = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\app.py'
CWD = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai'

# 1. 杀 5008 端口
for line in subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout.split('\n'):
    if ':5008' in line and 'LISTENING' in line:
        pid = line.split()[-1]
        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, text=True)
        print(f'killed {pid}')

time.sleep(3)

# 2. 杀所有 mobile_api_ai/app.py python 进程
ps_cmd = 'Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*mobile_api_ai*app.py*"} | Select-Object Id'
ps_result = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd],
                           capture_output=True, text=True)
print('ps:', ps_result.stdout[:200])

# 3. 用 powershell 杀
kill_cmd = 'Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like "*mobile_api_ai*app.py*"} | Stop-Process -Force'
subprocess.run(['powershell', '-NoProfile', '-Command', kill_cmd], capture_output=True, text=True)
time.sleep(3)

# 4. 启动新 5008
proc = subprocess.Popen(
    [PY, APP],
    cwd=CWD,
    creationflags=subprocess.CREATE_NEW_CONSOLE
)
print(f'started PID {proc.pid}')

# 5. 等待 + 验证
for i in range(20):
    time.sleep(1)
    try:
        r = requests.post('http://127.0.0.1:5008/api/login',
                          json={'username': '微风细雨'}, timeout=3)
        data = r.json().get('data', {})
        token = data.get('token', '')
        if token:
            print(f'✅ 5008 token 颁发成功 (i={i}s)')
            print(f'   token: {token[:60]}...')
            print(f'   user_id: {data.get("user_id", "NONE")}')

            # 验证 token 鉴权
            r2 = requests.post(
                'http://127.0.0.1:5008/api/attendance',
                headers={'Authorization': f'Bearer {token}'},
                json={'action': 'check-in'},
                timeout=5,
            )
            print(f'   用 token 调 attendance: HTTP {r2.status_code}')
            break
    except Exception as e:
        if i < 19:
            continue
        print(f'❌ 启动超时: {e}')
else:
    # 循环跑完没 break
    print('❌ 20 秒后仍未拿到 token')
    r = requests.get('http://127.0.0.1:5008/api/health', timeout=3)
    print(f'health: {r.status_code} {r.text[:200]}')
