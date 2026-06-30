# -*- coding: utf-8 -*-
"""启动 E2E 测试环境"""
import os, time, socket, subprocess

PYTHON = r'C:\Users\lenovo\AppData\Local\Python\bin\pythonw3.14-64.exe'
WORK_DIR = r'd:\yuan\不锈钢网带跟单3.0'
MOBILE_DIR = os.path.join(WORK_DIR, 'mobile_api_ai')

SERVICES = [
    {'name': '调度中心-5003', 'script': 'standalone_dispatch_server.py', 'port': 5003, 'cwd': MOBILE_DIR},
    {'name': '桌面Web-5001',  'script': 'server.py',                   'port': 5001, 'cwd': os.path.join(WORK_DIR, 'desktop_web')},
]

def kill_port(port):
    try:
        r = subprocess.run(f'netstat -ano | findstr ":{port} " | findstr LISTENING',
                          shell=True, capture_output=True, text=True, timeout=5)
        for line in r.stdout.strip().split('\n'):
            parts = line.strip().split()
            if len(parts) >= 5:
                pid = parts[4]
                try:
                    subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, timeout=5)
                    print(f'  杀旧进程 PID={pid}')
                except: pass
    except: pass

def check_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(2)
        s.connect(('127.0.0.1', port))
        s.close()
        return True
    except:
        return False

def main():
    print('=' * 60)
    print('启动 E2E 测试环境')
    print('=' * 60)
    print(f'Python: {PYTHON}')

    for svc in SERVICES:
        kill_port(svc['port'])
    time.sleep(2)

    for svc in SERVICES:
        print(f'  启动 {svc["name"]}...')
        script = os.path.join(svc['cwd'], svc['script'])
        print(f'  {PYTHON} {script}')
        proc = subprocess.Popen(
            [PYTHON, script],
            cwd=svc['cwd'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
        print(f'  PID={proc.pid}')

    print('\n等待服务就绪...')
    ready = {}
    for i in range(20):
        for svc in SERVICES:
            if svc['port'] not in ready and check_port(svc['port']):
                ready[svc['port']] = True
                print(f'  ✅ {svc["name"]} 就绪 ({(i+1)*2}s)')
        if len(ready) == len(SERVICES):
            break
        time.sleep(2)
    else:
        print('  ⚠️ 等待超时')

    print('=' * 60)
    all_ok = True
    for svc in SERVICES:
        ok = check_port(svc['port'])
        print(f'  {svc["name"]}: {"✅" if ok else "❌"}')
        if not ok: all_ok = False
    print('=' * 60)
    if all_ok:
        print('\n✅ 全部服务已就绪！')
    return all_ok

if __name__ == '__main__':
    import sys
    ok = main()
    sys.exit(0 if ok else 1)
