#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone server starter - 绕过 PowerShell 问题
"""
import sys
import os
import subprocess
import time
import threading
from pathlib import Path

# 设置编码
if sys.platform == 'win32':
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'Chinese_People\'s Republic of China.936')
    except:
        pass

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONLEGACYWINDOWSSTDIO'] = 'utf-8'

PYTHON = sys.executable
PROJECT_ROOT = Path(r"d:\yuan\不锈钢网带跟单3.0")
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

def kill_port(port):
    """关闭占用端口的进程"""
    try:
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, shell=True)
        for line in result.stdout.splitlines():
            if f':{port}' not in line:
                continue
            if 'LISTENING' not in line:
                continue
            parts = line.strip().split()
            if parts and parts[-1].isdigit():
                subprocess.run(['taskkill', '/F', '/PID', parts[-1]], capture_output=True, shell=True)
                print(f"[端口] 已关闭端口 {port} 的进程")
    except:
        pass

def start_server():
    """启动服务器"""
    port = 5008
    script = PROJECT_ROOT / "mobile_api_ai" / "app.py"

    print("="*60)
    print("不锈钢网带跟单系统 - 服务器启动")
    print("="*60)
    print(f"Python: {PYTHON}")
    print(f"端口: {port}")
    print(f"脚本: {script}")

    log_file = LOG_DIR / "mobile_api.log"

    print("\n[1/2] 清理端口...")
    kill_port(port)
    time.sleep(1)

    print("[2/2] 启动服务器...")
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'

    proc = subprocess.Popen(
        [PYTHON, '-B', str(script)],
        cwd=str(PROJECT_ROOT / "mobile_api_ai"),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    print(f"PID: {proc.pid}")
    print(f"日志: {log_file}")

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
        except Exception as e:
            print(f"异常: {e}")

    t = threading.Thread(target=monitor, daemon=True)
    t.start()

    print("\n等待启动 (5秒)...")
    time.sleep(5)

    if proc.poll() is None:
        print(f"\n✅ 服务已启动: http://localhost:{port}")
    else:
        print("\n❌ 服务启动失败")
        return None, [], []

    print(f"\n监控 60 秒...")
    for i in range(60):
        time.sleep(1)
        if proc.poll() is not None:
            print("服务已退出")
            break
        if i % 10 == 9:
            print(f"  [{i+1}/60] 运行中...")

    print("\n" + "="*60)
    print(f"错误: {len(errors)} | 警告: {len(warnings)}")

    if errors:
        print("\n错误:")
        for e in errors[:10]:
            print(f"  - {e}")

    if warnings:
        print("\n警告:")
        for w in warnings[:10]:
            print(f"  - {w}")

    if buffer:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write('\n'.join(buffer) + '\n')

    # 关闭
    if proc.poll() is None:
        proc.terminate()
        proc.wait()

    return proc, errors, warnings

if __name__ == '__main__':
    proc, errors, warnings = start_server()
    print("\n完成!")
