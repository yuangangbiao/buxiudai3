#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import time
import signal
import threading
from pathlib import Path

PYTHON = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe"
PROJECT_ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

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
        print(f"[端口清理] 异常: {e}")

print("="*60)
print("不锈钢网带跟单系统 - 直接启动")
print("="*60)

port = 5008
script = PROJECT_ROOT / "mobile_api_ai" / "app.py"
cwd = PROJECT_ROOT / "mobile_api_ai"

print(f"\n启动 报工程序 (端口 {port})...")
print(f"脚本: {script}")

kill_port_process(port)
time.sleep(1)

log_file = LOG_DIR / "mobile_api.log"
with open(log_file, 'w', encoding='utf-8') as f:
    f.write(f"{'='*60}\n")
    f.write(f"服务器: 报工程序\n")
    f.write(f"端口: {port}\n")
    f.write(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"{'='*60}\n\n")

env = os.environ.copy()
env['PYTHONDONTWRITEBYTECODE'] = '1'

print("\n[启动] 正在启动服务...")

proc = subprocess.Popen(
    [PYTHON, '-B', str(script)],
    cwd=str(cwd),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    universal_newlines=True
)

print(f"[启动] 进程 PID={proc.pid}")

buffer = []
start_time = time.time()
errors = []
warnings = []

def monitor():
    global buffer, errors, warnings
    try:
        while proc.poll() is None:
            line = proc.stdout.readline()
            if line:
                line = line.strip()
                print(f"[报工程序] {line}")

                # 检测错误和警告
                lower_line = line.lower()
                if any(kw in lower_line for kw in ['error', 'exception', 'fail', 'traceback']):
                    errors.append(line)
                elif any(kw in lower_line for kw in ['warning', 'warn']):
                    warnings.append(line)

                buffer.append(f"{time.strftime('%H:%M:%S')} | {line}")
                if len(buffer) >= 20:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write('\n'.join(buffer) + '\n')
                    buffer = []
            time.sleep(0.1)

        # 处理剩余输出
        for line in proc.stdout:
            line = line.strip()
            if line:
                print(f"[报工程序] {line}")
                lower_line = line.lower()
                if any(kw in lower_line for kw in ['error', 'exception', 'fail', 'traceback']):
                    errors.append(line)
                elif any(kw in lower_line for kw in ['warning', 'warn']):
                    warnings.append(line)
                buffer.append(f"{time.strftime('%H:%M:%S')} | {line}")

        if buffer:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write('\n'.join(buffer) + '\n')

    except Exception as e:
        print(f"日志监控异常: {e}")

t = threading.Thread(target=monitor, daemon=True)
t.start()

# 等待启动
print("\n[等待] 等待服务启动...")
for i in range(10):
    time.sleep(1)
    elapsed = time.time() - start_time
    if proc.poll() is None:
        print(f"[{i+1}/10] 服务运行中... ({elapsed:.1f}s)")
    else:
        print(f"[{i+1}/10] 服务未启动, 继续等待...")

if proc.poll() is None:
    print(f"\n✅ 报工程序 启动成功 (http://localhost:{port})")
    print(f"日志文件: {log_file}")
else:
    print(f"\n❌ 报工程序 启动失败")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n❌ 启动失败\n")
    sys.exit(1)

# 保持运行并收集日志
print("\n[监控] 持续监控中 (Ctrl+C 停止)...")
try:
    while proc.poll() is None:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n[停止] 正在关闭服务器...")

# 最终统计
print("\n" + "="*60)
print("日志收集结果")
print("="*60)
print(f"错误数量: {len(errors)}")
print(f"警告数量: {len(warnings)}")
print(f"日志文件: {log_file}")

if errors:
    print("\n错误详情:")
    for e in errors[:10]:  # 只显示前10个
        print(f"  - {e}")

if warnings:
    print("\n警告详情:")
    for w in warnings[:10]:  # 只显示前10个
        print(f"  - {w}")

# 关闭进程
print("\n[停止] 正在关闭服务器...")
proc.terminate()
try:
    proc.wait(timeout=5)
    print("[完成] 服务器已关闭")
except:
    proc.kill()
    print("[完成] 服务器已强制关闭")

# 保存最终日志
if buffer:
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write('\n'.join(buffer) + '\n')

print("\n[完成] 日志已保存")
