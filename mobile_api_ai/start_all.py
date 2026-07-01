# -*- coding: utf-8 -*-
"""
启动所有服务
- 移动报工API (端口 5008)
- 企业微信机器人 (端口 5003)
"""
import sys
import os
import subprocess
import time
import threading
import signal

# 确保在正确的目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

processes = []

def print_banner():
    print()
    print('=' * 60)
    print('  不锈钢网带跟单系统 - 智能服务启动')
    print('=' * 60)
    print()

def start_mobile_report_api():
    """启动移动报工API"""
    print('[启动] 移动报工API (端口 5008)...')
    try:
        proc = subprocess.Popen(
            [sys.executable, 'app.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        processes.append(proc)
        print('[成功] 移动报工API已启动')
        return proc
    except Exception as e:
        print(f'[失败] 移动报工API启动失败: {e}')
        return None

def start_wechat_bot():
    """启动企业微信机器人"""
    print('[启动] 企业微信机器人 (端口 5003)...')
    try:
        proc = subprocess.Popen(
            [sys.executable, 'wechat_server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        processes.append(proc)
        print('[成功] 企业微信机器人已启动')
        return proc
    except Exception as e:
        print(f'[失败] 企业微信机器人启动失败: {e}')
        return None

def monitor_process(proc, name):
    """监控进程输出"""
    try:
        for line in proc.stdout:
            line = line.strip()
            if line:
                print(f'[{name}] {line}')
    except Exception as e:
        print(f'[监控] 进程 {name} 输出读取异常: {e}')

def signal_handler(sig, frame):
    """处理终止信号"""
    print('\n[关闭] 正在关闭所有服务...')
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=int(os.environ.get('REQUEST_TIMEOUT_QUICK', '3')))
        except Exception as e:
            print(f'[关闭] 进程终止失败，尝试强制关闭: {e}')
            try:
                proc.kill()
            except Exception as e2:
                print(f'[关闭] 进程强制关闭失败: {e2}')
    print('[关闭] 所有服务已关闭')
    sys.exit(0)

def main():
    print_banner()
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动服务
    mobile_proc = start_mobile_report_api()
    time.sleep(3)  # 等待移动报工API启动
    wechat_proc = start_wechat_bot()
    
    print()
    print('=' * 60)
    print('  所有服务已启动!')
    print('=' * 60)
    print()
    print('服务地址:')
    print('  - 移动报工API: http://localhost:5008')
    print('  - 企业微信机器人: http://localhost:5003')
    print()
    print('按 Ctrl+C 关闭所有服务')
    print()
    
    # 启动监控线程
    if mobile_proc:
        threading.Thread(
            target=monitor_process,
            args=(mobile_proc, '移动报工API'),
            daemon=True
        ).start()
    
    if wechat_proc:
        threading.Thread(
            target=monitor_process,
            args=(wechat_proc, '微信机器人'),
            daemon=True
        ).start()
    
    # 等待
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == '__main__':
    main()
