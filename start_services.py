#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单启动脚本 - 启动所有服务
"""
import sys
import os
import subprocess
import time
import webbrowser
from pathlib import Path

# 设置项目目录
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# 加载环境变量
env_file = project_dir / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# 服务配置
SERVICES = [
    {
        'name': '移动报工API',
        'script': 'mobile_api_ai/app.py',
        'cwd': 'mobile_api_ai',
        'port': 5000,
        'url': 'http://localhost:5000'
    },
    {
        'name': '企业微信机器人',
        'script': 'mobile_api_ai/wechat_server.py',
        'cwd': 'mobile_api_ai',
        'port': 5003,
        'url': 'http://localhost:5003'
    },
    {
        'name': '大屏服务器',
        'script': 'desktop/views/dashboard/dashboard_server.py',
        'cwd': 'desktop/views/dashboard',
        'port': 5005,
        'url': 'http://localhost:5005'
    },
    {
        'name': '轮询监控器',
        'script': 'mobile_api_ai/poll_monitor.py',
        'cwd': 'mobile_api_ai',
        'port': None,
        'url': None
    }
]

processes = []

def start_service(service):
    """启动单个服务"""
    print(f"\n{'='*60}")
    print(f"正在启动: {service['name']}")
    print(f"{'='*60}")
    
    script_path = project_dir / service['script']
    cwd_path = project_dir / service['cwd']
    
    if not script_path.exists():
        print(f"❌ 脚本不存在: {script_path}")
        return None
    
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script_path)],
            cwd=str(cwd_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            errors='ignore'
        )
        print(f"✅ {service['name']} 已启动 (PID: {proc.pid})")
        if service['url']:
            print(f"📄 访问地址: {service['url']}")
        return proc
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return None

def main():
    print("不锈钢网带跟单系统 - 服务启动")
    print("="*60)
    
    # 启动所有服务
    for service in SERVICES:
        proc = start_service(service)
        if proc:
            processes.append((service['name'], proc))
        time.sleep(2)  # 等待一下避免同时启动
    
    print("\n" + "="*60)
    print("所有服务启动完成！")
    print("="*60)
    
    # 打开主要页面
    print("\n正在打开主要页面...")
    time.sleep(2)
    
    for service in SERVICES:
        if service['url']:
            try:
                webbrowser.open(service['url'])
                time.sleep(1)
            except Exception as e:
                logger.warning(f"无法打开浏览器: {e}")
    
    print("\n提示: 按 Ctrl+C 停止所有服务")
    
    try:
        # 监控进程
        while True:
            time.sleep(1)
            # 检查进程是否还在运行
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"⚠️ {name} 已停止 (退出码: {proc.returncode})")
    except KeyboardInterrupt:
        print("\n正在停止所有服务...")
        for name, proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=3)
                print(f"✅ {name} 已停止")
            except Exception:
                proc.kill()
                print(f"⚠️ {name} 已强制停止")
        print("所有服务已停止")

if __name__ == "__main__":
    main()
