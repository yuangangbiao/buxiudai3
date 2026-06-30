# -*- coding: utf-8 -*-
"""
重启 6 个服务 - v3.6.4 治理：修复日志爆炸 bug 后应用新配置
按顺序重启：5003 → 5008 → 5001 → 5002 → 5010 → 8008
每步间隔 5 秒
"""
import subprocess
import sys
import time
import os

PYTHON = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe"
WORK_DIR = r"D:\yuan\不锈钢网带跟单3.0"

SERVICES = [
    # (端口, 启动脚本, 服务描述)
    (5003, "start_5003.py", "调度中心"),
    (5008, "start_5008.py", "移动端报工"),
    (5001, "start_5001.py", "desktop_web"),
    (5002, "start_5002.py", "容器中心"),
    (5010, "start_5010.py", "库存管理"),
    (8008, "start_8008.py", "Sync Bridge"),
]

# 已知的现有 PID（用于先停止）
EXISTING_PIDS = [15684, 16492, 29560, 2352, 17272]  # 5003/5008/5001/5002/8008

def kill_existing():
    """停止所有现有服务"""
    print("=" * 60)
    print("Step 1: 停止所有现有服务")
    print("=" * 60)
    for pid in EXISTING_PIDS:
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print(f"  [KILLED] PID {pid}")
            else:
                print(f"  [NOT FOUND] PID {pid}: {result.stderr.strip()[:80]}")
        except Exception as e:
            print(f"  [ERROR] PID {pid}: {e}")

    # 多等几秒确保完全关闭
    print("  等待 5 秒确保所有进程关闭...")
    time.sleep(5)

def kill_remaining_python():
    """强制清理所有剩余的 Python 进程（保留 6 个目标服务的子进程）"""
    print()
    print("Step 1.5: 清理其他相关 Python 进程")
    result = subprocess.run(
        ["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine", "/format:list"],
        capture_output=True, text=True, timeout=30
    )
    print(f"  当前 Python 进程:\n{result.stdout[:500]}")

def start_services():
    """按顺序启动 6 个服务"""
    print()
    print("=" * 60)
    print("Step 2: 按顺序启动 6 个服务")
    print("=" * 60)
    for port, script, desc in SERVICES:
        print(f"\n[START] {port} {desc} ({script})")
        try:
            proc = subprocess.Popen(
                [PYTHON, script],
                cwd=WORK_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            print(f"  启动成功 PID={proc.pid}")
            time.sleep(5)  # 间隔 5 秒
        except Exception as e:
            print(f"  [ERROR] 启动失败: {e}")

def verify():
    """验证服务是否启动"""
    print()
    print("=" * 60)
    print("Step 3: 验证服务状态")
    print("=" * 60)
    time.sleep(10)  # 等待所有服务完全启动
    result = subprocess.run(
        ["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine", "/format:list"],
        capture_output=True, text=True, timeout=30
    )
    print(f"\n  启动后的 Python 进程:\n{result.stdout[:2000]}")

if __name__ == "__main__":
    kill_existing()
    kill_remaining_python()
    start_services()
    verify()
    print()
    print("=" * 60)
    print("重启完成。请等待 1 小时观察 cloud_relay/ 等目录的 .log 数量。")
    print("=" * 60)
