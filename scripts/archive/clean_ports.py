#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理端口占用的进程
"""
import subprocess
import re

def get_processes_on_port(port):
    """获取指定端口上的进程"""
    result = subprocess.run(
        ['netstat', '-ano'],
        capture_output=True,
        text=True
    )
    processes = []
    for line in result.stdout.split('\n'):
        if f':{port}' in line and 'LISTENING' in line:
            match = re.search(r'\b(\d+)\s*$', line)
            if match:
                pid = match.group(1)
                processes.append(pid)
    return processes

def kill_process(pid):
    """终止进程"""
    try:
        subprocess.run(
            ['taskkill', '/F', '/PID', pid],
            capture_output=True,
            text=True
        )
        return True
    except Exception as e:
        print(f"终止进程 {pid} 失败: {e}")
        return False

if __name__ == '__main__':
    ports = [5005]
    
    for port in ports:
        pids = get_processes_on_port(port)
        if pids:
            print(f"端口 {port} 被以下进程占用: {', '.join(pids)}")
            for pid in pids:
                print(f"正在终止 PID {pid}...")
                if kill_process(pid):
                    print(f"  ✅ PID {pid} 已终止")
        
        # 再次检查
        pids = get_processes_on_port(port)
        if not pids:
            print(f"✅ 端口 {port} 已清理")
        else:
            print(f"❌ 端口 {port} 仍被占用: {', '.join(pids)}")
