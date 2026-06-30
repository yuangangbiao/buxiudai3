#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接执行服务器启动代码
"""
import subprocess
import sys
import os
import time
import threading
from pathlib import Path

PYTHON = sys.executable
PROJECT_ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

port = 5008
script = PROJECT_ROOT / "mobile_api_ai" / "app.py"
cwd = PROJECT_ROOT / "mobile_api_ai"

print("="*60)
print("不锈钢网带跟单系统 - 服务器启动")
print("="*60)
print(f"\nPython: {PYTHON}")
print(f"脚本: {script}")
print(f"端口: {port}")

log_file = LOG_DIR / "mobile_api.log"
with open(log_file, 'w', encoding='utf-8') as f:
    f.write(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

env = os.environ.copy()
env['PYTHONDONTWRITEBYTECODE'] = '1'

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

print(f"\n进程 PID: {proc.pid}")
print(f"日志文件: {log_file}\n")

buffer = []
errors = []
warnings = []

def monitor():
    global buffer, errors, warnings
    try:
        while proc.poll() is None:
            line = proc.stdout.readline()
            if line:
                line = line.strip()
                print(line)
                lower = line.lower()
                if any(kw in lower for kw in ['error', 'exception', 'fail', 'traceback']):
                    errors.append(line)
                elif any(kw in lower for kw in ['warning', 'warn']):
                    warnings.append(line)
                buffer.append(f"{time.strftime('%H:%M:%S')} | {line}")
                if len(buffer) >= 20:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write('\n'.join(buffer) + '\n')
                    buffer = []
            time.sleep(0.1)
        running = False
    except Exception as e:
        print(f"异常: {e}")

t = threading.Thread(target=monitor, daemon=True)
t.start()

print("等待启动 (5秒)...")
time.sleep(5)

if proc.poll() is None:
    print(f"\n✅ 服务启动成功! http://localhost:{port}")
else:
    print("\n❌ 服务启动失败")
    sys.exit(1)

print(f"\n监控 60 秒...")
for i in range(60):
    time.sleep(1)
    if proc.poll() is not None:
        break
    if i % 10 == 9:
        print(f"  [{i+1}/60] 运行中...")

print("\n" + "="*60)
print(f"错误: {len(errors)} | 警告: {len(warnings)}")
print(f"日志: {log_file}")

if errors:
    print("\n错误:")
    for e in errors[:5]:
        print(f"  - {e}")

if warnings:
    print("\n警告:")
    for w in warnings[:5]:
        print(f"  - {w}")

if buffer:
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write('\n'.join(buffer) + '\n')

if proc.poll() is None:
    proc.terminate()
    proc.wait()
print("\n[完成]")
