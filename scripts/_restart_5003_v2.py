"""P1-R1 第二步: 强制重启 5003 让 outbox 轮询读新表"""
import subprocess
import time
import pymysql
import requests

# 1. 验证表存在
conn = pymysql.connect(
    host='127.0.0.1', port=3306, user='root', password='88888888',
    database='container_center', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
)
with conn.cursor() as cur:
    cur.execute("SHOW TABLES LIKE 'outbox'")
    print('outbox exists:', bool(cur.fetchone()))
    cur.execute('SELECT COUNT(*) AS cnt FROM outbox')
    print('outbox rows:', cur.fetchone()['cnt'])
conn.close()

# 2. 杀 5003
print('\n--- 杀 5003 ---')
for line in subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout.split('\n'):
    if ':5003' in line and 'LISTENING' in line:
        pid = line.split()[-1]
        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, text=True)
        print(f'killed {pid}')

time.sleep(5)

# 3. 重启 5003
proc = subprocess.Popen(
    [r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe',
     r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\standalone_dispatch_server.py'],
    cwd=r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai',
    creationflags=subprocess.CREATE_NEW_CONSOLE
)
print(f'started PID {proc.pid}')

# 4. 等 20s
print('等 20s...')
time.sleep(20)

# 5. 看新日志
with open(r'd:\yuan\不锈钢网带跟单3.0\logs\e2e_20260623\5003.err.log',
          'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()
ob = [l for l in lines if 'outbox' in l.lower()]
print(f'\noutbox 总数: {len(ob)}')
print('最近 5 条:')
for l in ob[-5:]:
    print(f'  {l.strip()[:200]}')

# 6. 5003 健康
r = requests.get('http://127.0.0.1:5003/', timeout=3)
print(f'\n5003 status: {r.status_code}')
