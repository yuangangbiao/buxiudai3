#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器启动和日志监控脚本
"""
import subprocess
import sys
import os
import time
import signal
import signal
from pathlib import Path

PYTHON = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe"
PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

SERVERS = [
    {
        'name': '报工程序',
        'script': 'mobile_api_ai/app.py',
        'cwd': 'mobile_api_ai',
        'port': 5008,
    },
]

def kill_all_python():
    """杀掉所有 Python 进程"""
    my_pid = os.getpid()
    killed = 0
    try:
        result = subprocess.run(
            ['tasklist', '/FO', 'CSV', '/NH'],
            capture_output=True, text=True, shell=True
        )
        for line in result.stdout.splitlines():
            if 'python' not in line.lower():
                continue
            parts = line.replace('"', '').split(',')
            if len(parts) >= 2:
                pid_str = parts[1].strip()
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if pid != my_pid and pid != os.getppid():
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                                      capture_output=True, shell=True)
                        killed += 1
                        print(f"[清理] 已杀掉进程 PID={pid}")
    except Exception as e:
        print(f"[清理] 异常: {e}")
    return killed

def kill_port_process(port):
    """关闭占用指定端口的进程"""
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            shell=True
        )
        for line in result.stdout.splitlines():
            if f':{port}' not in line:
                continue
            if 'LISTENING' not in line and 'ESTABLISHED' not in line:
                continue
            parts = line.strip().split()
            if not parts:
                continue
            pid = parts[-1]
            if pid.isdigit():
                subprocess.run(['taskkill', '/F', '/PID', pid],
                              capture_output=True, text=True, shell=True)
                print(f"[端口清理] 已关闭端口 {port} 的进程 PID={pid}")
    except Exception as e:
        print(f"[端口清理] 关闭端口 {port} 时异常: {e}")

def start_server(server):
    """启动单个服务器"""
    port = server['port']
    print(f"\n{'='*60}")
    print(f"启动 {server['name']} (端口 {port})...")
    print('='*60)

    kill_port_process(port)
    time.sleep(1)

    script_path = PROJECT_ROOT / server['script']
    cwd_path = PROJECT_ROOT / server['cwd']

    log_file = LOG_DIR / f"{server['name']}.log"

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"{'='*60}\n")
        f.write(f"服务器: {server['name']}\n")
        f.write(f"端口: {port}\n")
        f.write(f"脚本: {script_path}\n")
        f.write(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")

    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'

    proc = subprocess.Popen(
        [PYTHON, '-B', str(script_path)],
        cwd=str(cwd_path),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    print(f"[启动] 进程 PID={proc.pid}")
    print(f"[日志] {log_file}")

    def monitor():
        """监控输出并写入日志"""
        try:
            while proc.poll() is None:
                line = proc.stdout.readline()
                if line:
                    line = line.strip()
                    print(f"[{server['name']}] {line}")
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(f"{time.strftime('%H:%M:%S')} | {line}\n")
                time.sleep(0.1)

            for line in proc.stdout:
                line = line.strip()
                if line:
                    print(f"[{server['name']}] {line}")
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(f"{time.strftime('%H:%M:%S')} | {line}\n")

            returncode = proc.poll()
            print(f"⚠️ 服务器 {server['name']} 异常退出, 返回码: {returncode}")
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"服务器异常退出, 返回码: {returncode}\n")
                f.write(f"{'='*60}\n")
        except Exception as e:
            print(f"日志监控异常: {e}")

    import threading
    t = threading.Thread(target=monitor, daemon=True)
    t.start()

    time.sleep(3)

    if proc.poll() is None:
        print(f"✅ {server['name']} 启动成功")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n✅ {server['name']} 启动成功\n")
        return proc
    else:
        print(f"❌ {server['name']} 启动失败")
        return None

def main():
    print("="*60)
    print("不锈钢网带跟单系统 - 服务器启动器")
    print("="*60)

    print("\n[准备] 清理旧进程...")
    killed = kill_all_python()
    print(f"[清理] 已清理 {killed} 个旧进程")

    processes = []
    for server in SERVERS:
        proc = start_server(server)
        if proc:
            processes.append((server, proc))

    print(f"\n{'='*60}")
    print(f"启动完成: {len(processes)}/{len(SERVERS)} 成功")
    print('='*60)

    if processes:
        print("\n进程保持中 (Ctrl+C 停止)...")
        try:
            while True:
                time.sleep(1)
                for server, proc in processes[:]:
                    if proc.poll() is not None:
                        print(f"⚠️ {server['name']} 已退出")
                        processes.remove((server, proc))
                if not processes:
                    print("所有服务器已退出")
                    break
        except KeyboardInterrupt:
            print("\n[停止] 正在关闭服务器...")
            for server, proc in processes:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    print(f"✅ {server['name']} 已停止")
                except:
                    proc.kill()
                    print(f"✅ {server['name']} 已强制停止")
            print("[完成] 所有服务器已关闭")

if __name__ == '__main__':
    main()
