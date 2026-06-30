#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大屏服务启动器 - 自动处理端口冲突
"""
import subprocess
import sys
import os
import time
import re

def get_pids_on_port(port):
    """获取占用指定端口的进程ID列表"""
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            timeout=10
        )
        pids = []
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                match = re.search(r'\b(\d+)\s*$', line)
                if match:
                    pids.append(match.group(1))
        return pids
    except Exception as e:
        print(f"获取端口信息失败: {e}")
        return []

def kill_pids(pids):
    """终止进程列表"""
    for pid in pids:
        try:
            subprocess.run(
                ['taskkill', '/F', '/PID', pid],
                capture_output=True,
                text=True,
                timeout=5
            )
            print(f"已终止进程: {pid}")
        except Exception as e:
            print(f"终止进程 {pid} 失败: {e}")

def start_dashboard():
    """启动大屏服务"""
    port = 5005
    
    # 清理端口
    print(f"=== 检查端口 {port} ===")
    pids = get_pids_on_port(port)
    if pids:
        print(f"端口 {port} 被占用: {', '.join(pids)}")
        print("正在清理...")
        kill_pids(pids)
        time.sleep(1)
        
        # 再次检查
        pids = get_pids_on_port(port)
        if pids:
            print(f"警告: 端口 {port} 仍被占用: {', '.join(pids)}")
    
    # 启动服务
    print(f"\n=== 启动大屏服务 (端口 {port}) ===")
    os.chdir(r"d:\yuan\不锈钢网带跟单3.0\desktop\views\dashboard")
    
    proc = subprocess.Popen(
        [sys.executable, 'dashboard_server.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # 实时输出日志
    try:
        while proc.poll() is None:
            line = proc.stdout.readline()
            if line:
                print(line.strip())
                sys.stdout.flush()
        # 进程结束后打印剩余输出
        for line in proc.stdout:
            print(line.strip())
    except KeyboardInterrupt:
        print("\n收到终止信号，正在停止服务...")
        proc.terminate()
        proc.wait()

if __name__ == '__main__':
    start_dashboard()
