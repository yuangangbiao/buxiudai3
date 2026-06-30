#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys

print("="*60)
print("安装 Playwright")
print("="*60)

NODE_BIN = r"C:\Program Files\nodejs\node.exe"
npm = r"C:\Program Files\nodejs\npm.cmd"

print("\n安装 Playwright...")
result = subprocess.run(
    [npm, 'install', 'playwright', '--save-dev'],
    cwd=r"d:\yuan\不锈钢网带跟单3.0",
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

if result.stdout:
    print(result.stdout)
if result.stderr:
    print("错误:", result.stderr)

print(f"\n安装完成，退出代码: {result.returncode}")

# 安装浏览器
print("\n安装 Chromium 浏览器...")
result = subprocess.run(
    [NODE_BIN, '-e', 'require("playwright").chromium.launch().then(b => { console.log("浏览器安装成功"); b.close(); }).catch(e => { console.error("错误:", e.message); process.exit(1); })'],
    cwd=r"d:\yuan\不锈钢网带跟单3.0",
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    timeout=120
)

if result.stdout:
    print(result.stdout)
if result.stderr:
    print("错误:", result.stderr)

print("\n完成!")
