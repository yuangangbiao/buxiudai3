#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
嵌入式服务器启动器 - 直接启动，不依赖外部命令
"""
import subprocess
import sys
import os
import time
import threading
import signal
from pathlib import Path

# 设置 Python 路径
PYTHON = sys.executable
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
print("不锈钢网带跟单系统 - 服务器启动与测试")
print("="*60)

port = 5008
script = PROJECT_ROOT / "mobile_api_ai" / "app.py"
cwd = PROJECT_ROOT / "mobile_api_ai"

print(f"\n[1/3] 准备启动报工程序 (端口 {port})...")
print(f"       脚本: {script}")

# 清理端口
print("\n[2/3] 清理端口...")
kill_port_process(port)
time.sleep(1)

# 创建日志文件
log_file = LOG_DIR / "mobile_api.log"
with open(log_file, 'w', encoding='utf-8') as f:
    f.write(f"{'='*60}\n")
    f.write(f"服务器: 报工程序\n")
    f.write(f"端口: {port}\n")
    f.write(f"启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"{'='*60}\n\n")

# 设置环境
env = os.environ.copy()
env['PYTHONDONTWRITEBYTECODE'] = '1'

# 启动进程 - 使用 CREATE_NEW_CONSOLE 避免父进程影响
print("\n[3/3] 启动服务器...")
print(f"       Python: {PYTHON}")
print(f"       进程创建标志: CREATE_NEW_CONSOLE")

proc = subprocess.Popen(
    [PYTHON, '-B', str(script)],
    cwd=str(cwd),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    universal_newlines=True,
    creationflags=subprocess.CREATE_NEW_CONSOLE
)

print(f"       进程 PID={proc.pid}")
print(f"       日志: {log_file}")

# 监控变量
buffer = []
errors = []
warnings = []
running = True

def monitor():
    global buffer, errors, warnings, running
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
        running = False
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
        running = False

# 启动监控线程
t = threading.Thread(target=monitor, daemon=True)
t.start()

# 等待启动
print("\n[等待] 等待服务启动 (最多 10 秒)...")
for i in range(10):
    time.sleep(1)
    if proc.poll() is None:
        print(f"       [{i+1}/10] 服务运行中...")
        break
    print(f"       [{i+1}/10] 等待中...")
else:
    print("\n⚠️ 服务未能在 10 秒内启动，继续监控...")

if proc.poll() is None:
    print(f"\n✅ 报工程序 启动成功!")
    print(f"   访问地址: http://localhost:{port}")
else:
    print(f"\n❌ 报工程序 启动失败")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n❌ 启动失败\n")
    sys.exit(1)

# 持续监控 60 秒
print(f"\n[监控] 持续监控 60 秒以收集日志...")
for i in range(60):
    if proc.poll() is not None:
        print("\n⚠️ 服务已退出")
        break
    time.sleep(1)
    if i % 10 == 9:  # 每 10 秒提示
        print(f"       [{i+1}/60] 服务运行中...")

# 最终统计
print("\n" + "="*60)
print("日志收集结果")
print("="*60)
print(f"错误数量: {len(errors)}")
print(f"警告数量: {len(warnings)}")
print(f"日志文件: {log_file}")

if errors:
    print("\n❌ 错误详情:")
    for e in errors[:10]:
        print(f"   - {e}")
    if len(errors) > 10:
        print(f"   ... 还有 {len(errors) - 10} 个错误")

if warnings:
    print("\n⚠️ 警告详情:")
    for w in warnings[:10]:
        print(f"   - {w}")
    if len(warnings) > 10:
        print(f"   ... 还有 {len(warnings) - 10} 个警告")

# 保存最终日志
if buffer:
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write('\n'.join(buffer) + '\n')

# 关闭进程
print("\n[停止] 正在关闭服务器...")
if proc.poll() is None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
        print("[完成] 服务器已关闭")
    except:
        proc.kill()
        print("[完成] 服务器已强制关闭")
else:
    print("[完成] 服务器已自行退出")

print("\n[完成] 日志已保存到:")
print(f"   {log_file}")
print("\n现在可以使用 Playwright 进行浏览器测试...")
