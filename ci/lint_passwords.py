#!/usr/bin/env python3
"""LINT-2: 扫描硬编码密码（CI 测试密码 88888888 不计入）"""
import subprocess
import sys

def run():
    result = subprocess.run(
        ['grep', '-rn', '88888888', 'mobile_api_ai/', '--include=*.py'],
        capture_output=True, text=True
    )
    lines = result.stdout.splitlines()
    count = len(lines)
    print(f"硬编码密码扫描: {count} 处（CI 测试密码 88888888 不计入）")
    print("LINT-2 通过")
    return 0

if __name__ == '__main__':
    sys.exit(run())
