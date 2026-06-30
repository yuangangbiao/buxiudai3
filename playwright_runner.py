#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import os
from pathlib import Path

SKILL_DIR = r"C:\Users\lenovo\.trae-cn\skills\playwright-skill"
TEST_SCRIPT = r"d:\yuan\不锈钢网带跟单3.0\logs\playwright_mobile_test.js"
NODE_BIN = r"C:\Program Files\nodejs\node.exe"

print("="*60)
print("Playwright 浏览器测试")
print("="*60)
print(f"Skill 目录: {SKILL_DIR}")
print(f"测试脚本: {TEST_SCRIPT}")

# 检查文件是否存在
if not os.path.exists(TEST_SCRIPT):
    print(f"❌ 测试脚本不存在: {TEST_SCRIPT}")
    sys.exit(1)

if not os.path.exists(NODE_BIN):
    print(f"❌ Node.js 不存在: {NODE_BIN}")
    sys.exit(1)

print("\n正在启动 Playwright 测试...")

try:
    proc = subprocess.Popen(
        [NODE_BIN, 'run.js', TEST_SCRIPT],
        cwd=SKILL_DIR,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = proc.communicate(timeout=60)

    if stdout:
        print("\n输出:")
        print(stdout)

    if stderr:
        print("\n错误:")
        print(stderr)

    print(f"\n退出代码: {proc.returncode}")

except subprocess.TimeoutExpired:
    print("\n❌ 测试超时")
    proc.kill()
    sys.exit(1)
except Exception as e:
    print(f"\n❌ 执行失败: {e}")
    sys.exit(1)

print("\n测试完成!")
