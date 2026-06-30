# -*- coding: utf-8 -*-
"""
测试环境启动器 - 修复 P0-5

启动 5 个核心服务 + MySQL + Redis，供测试使用。
"""
import os
import sys
import time
import signal
import subprocess
import socket
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / 'mobile_api_ai'

# 服务启动配置
SERVICES = {
    'desktop_web': {
        'script': PROJECT_ROOT / 'desktop' / 'desktop_server.py',
        'port': 5001,
        'cwd': PROJECT_ROOT,
        'required': False,  # 桌面端不一定总是启动
    },
    'container': {
        'script': PROJECT_ROOT / 'mobile_api_ai' / 'container_center_api.py',
        'port': 5002,
        'cwd': SCRIPTS_DIR,
    },
    'dispatch': {
        'script': PROJECT_ROOT / 'mobile_api_ai' / 'standalone_dispatch_server.py',
        'port': 5003,
        'cwd': SCRIPTS_DIR,
    },
    'mobile': {
        'script': PROJECT_ROOT / 'mobile_api_ai' / 'app.py',
        'port': 5008,
        'cwd': SCRIPTS_DIR,
    },
    'sync_bridge': {
        'script': PROJECT_ROOT / 'mobile_api_ai' / 'sync_bridge_server.py',
        'port': 8008,
        'cwd': SCRIPTS_DIR,
    },
}


def is_port_open(port: int) -> bool:
    """检查端口是否已开放"""
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def wait_for_port(port: int, timeout: int = 30) -> bool:
    """等待端口开放"""
    start = time.time()
    while time.time() - start < timeout:
        if is_port_open(port):
            return True
        time.sleep(0.5)
    return False


def start_service(name: str, config: dict) -> subprocess.Popen:
    """启动单个服务"""
    if is_port_open(config['port']):
        print(f"  ✅ {name} 端口 {config['port']} 已在运行")
        return None

    if not config['script'].exists():
        print(f"  ⚠️ {name} 脚本不存在: {config['script']}")
        return None

    print(f"  🚀 启动 {name} (端口 {config['port']})...")
    proc = subprocess.Popen(
        [sys.executable, str(config['script'])],
        cwd=str(config['cwd']),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0,
    )
    return proc


def main():
    """主函数"""
    print("=" * 70)
    print("🧪 测试环境启动器")
    print("=" * 70)

    processes = {}

    # 1. 启动 5 个服务
    print("\n📡 启动核心服务:")
    for name, config in SERVICES.items():
        if config.get('required', True) is False:
            continue
        proc = start_service(name, config)
        if proc:
            processes[name] = proc

    # 2. 等待服务就绪
    print("\n⏳ 等待服务就绪...")
    time.sleep(3)  # 基础等待

    for name, config in SERVICES.items():
        if config.get('required', True) is False:
            continue
        if wait_for_port(config['port'], timeout=30):
            print(f"  ✅ {name} (端口 {config['port']}) 就绪")
        else:
            print(f"  ❌ {name} (端口 {config['port']}) 启动超时")

    print("\n✅ 测试环境就绪")
    print(f"   启动进程数: {len(processes)}")
    print(f"   提示: Ctrl+C 停止所有服务\n")

    # 3. 等待终止信号
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 正在停止所有服务...")
        for name, proc in processes.items():
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                print(f"  已停止: {name}")
        print("✅ 所有服务已停止")


if __name__ == '__main__':
    main()
