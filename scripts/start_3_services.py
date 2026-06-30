# -*- coding: utf-8 -*-
"""启动测试所需的三个服务（5008/5003/8008）— 改进版"""
import os
import time
import subprocess
import socket
import urllib.request

PYTHON = r'C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe'
WORK_DIR = os.path.dirname(os.path.dirname(__file__))
MOBILE_DIR = os.path.join(WORK_DIR, 'mobile_api_ai')

SERVICES = [
    {'name': '调度中心-5003', 'script': 'standalone_dispatch_server.py', 'port': 5003, 'cwd': MOBILE_DIR},
    {'name': '报工系统-5008', 'script': 'app.py', 'port': 5008, 'cwd': MOBILE_DIR},
    {'name': '同步桥-8008',   'script': 'sync_bridge_server.py', 'port': 8008, 'cwd': MOBILE_DIR},
]


def kill_port(port):
    """杀掉占用端口的进程"""
    result = subprocess.run(f'netstat -ano | findstr ":{port} " | findstr LISTENING',
                            shell=True, capture_output=True, text=True, timeout=5)
    for line in result.stdout.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) >= 5:
            pid = parts[4]
            try:
                subprocess.run(['taskkill', '/F', '/PID', pid],
                               capture_output=True, timeout=5)
                print(f'  杀掉旧进程 PID={pid} (端口{port})')
            except:
                pass


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
    print('启动测试所需服务')
    print('=' * 60)

    # 先杀旧进程
    for svc in SERVICES:
        kill_port(svc['port'])
    time.sleep(2)

    procs = []
    for svc in SERVICES:
        port = svc['port']
        print(f'  启动 {svc["name"]}...')
        proc = subprocess.Popen(
            [PYTHON, svc['script']],
            cwd=svc['cwd'],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        procs.append(proc)

    # 等待就绪
    print('\n等待服务就绪...')
    for i in range(20):
        all_ok = all(check_port(s['port']) for s in SERVICES)
        if all_ok:
            break
        time.sleep(2)

    print('\n' + '=' * 60)
    print('服务状态检查:')
    all_ok = True
    for svc in SERVICES:
        ok = check_port(svc['port'])
        status = '✅ 运行中' if ok else '❌ 未启动'
        if not ok:
            all_ok = False
        print(f'  {svc["name"]}: {status}')

    if all_ok:
        print('\n✅ 所有服务已就绪，可以进行测试！')
    else:
        print('\n⚠️  部分服务未启动')
        # 检查失败服务的进程
        for svc in SERVICES:
            if not check_port(svc['port']):
                print(f'\n检查 {svc["name"]} 进程状态...')
                result = subprocess.run(f'netstat -ano | findstr ":{svc["port"]} "',
                                        shell=True, capture_output=True, text=True, timeout=5)
                if result.stdout.strip():
                    print(f'  端口占用: {result.stdout.strip()}')
                else:
                    print(f'  端口未监听')

    print('=' * 60)

if __name__ == '__main__':
    main()
