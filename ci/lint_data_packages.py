#!/usr/bin/env python3
"""LINT-1: 扫描 data_packages SQL 残留"""
import subprocess
import sys

def run():
    result = subprocess.run(
        'grep -rEn "FROM data_packages|INTO data_packages|UPDATE data_packages" mobile_api_ai/ --include=*.py',
        shell=True, capture_output=True, text=True
    )
    lines = [l for l in result.stdout.splitlines()
             if 'data_packages_deprecated' not in l]
    count = len(lines)
    print(f"data_packages SQL 引用数: {count}")
    if count > 0:
        for l in lines:
            print(l)
        print(f"::error::发现 {count} 处 data_packages SQL 残留")
        return 1
    print("LINT-1 通过: 0 处残留")
    return 0

if __name__ == '__main__':
    sys.exit(run())
