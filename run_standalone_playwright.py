#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import os
from pathlib import Path

NODE_BIN = r"C:\Program Files\nodejs\node.exe"
TEST_SCRIPT = r"d:\yuan\不锈钢网带跟单3.0\standalone_playwright.js"

print("="*60)
print("Playwright 独立浏览器测试")
print("="*60)
print(f"测试脚本: {TEST_SCRIPT}")

if not os.path.exists(NODE_BIN):
    print(f"❌ Node.js 不存在: {NODE_BIN}")
    sys.exit(1)

if not os.path.exists(TEST_SCRIPT):
    print(f"❌ 测试脚本不存在: {TEST_SCRIPT}")
    sys.exit(1)

print("\n正在启动 Playwright 测试...")
print("(这将打开浏览器窗口)")

try:
    proc = subprocess.Popen(
        [NODE_BIN, TEST_SCRIPT],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = proc.communicate(timeout=120)

    if stdout:
        print("\n" + "="*60)
        print("测试输出:")
        print("="*60)
        print(stdout)

    if stderr:
        print("\n" + "="*60)
        print("错误输出:")
        print("="*60)
        print(stderr)

    print(f"\n退出代码: {proc.returncode}")

except subprocess.TimeoutExpired:
    print("\n❌ 测试超时 (120秒)")
    proc.kill()
    sys.exit(1)
except Exception as e:
    print(f"\n❌ 执行失败: {e}")
    sys.exit(1)

print("\n测试完成!")
