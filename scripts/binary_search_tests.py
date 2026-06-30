# -*- coding: utf-8 -*-
"""验证修复：运行关键测试组合"""
import subprocess

PYTHON = r"C:\Users\lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe"
ROOT = r"d:\yuan\不锈钢网带跟单3.0"

def run_tests(files, label):
    print(f"\n{'='*60}")
    print(f"Running: {label}")
    print('='*60)
    args = [PYTHON, "-m", "pytest", "-q", "--tb=no"] + files
    result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    lines = result.stdout.strip().split('\n')
    for line in lines[-20:]:
        print(line)
    if result.returncode != 0:
        print(f"\n*** Exit: {result.returncode}")
    return result.returncode

# 关键验证
run_tests([
    "tests/unit/models/test_order_crud_gaps.py",
    "tests/unit/models/test_order_dao.py",
], "test_order_crud_gaps + test_order_dao (was 42 failures)")

run_tests([
    "tests/unit/models/test_order_log.py",
    "tests/unit/models/test_order_crud_gaps.py",
    "tests/unit/models/test_order_dao.py",
], "test_order_log + order_crud_gaps + order_dao")

# 另外验证单独运行
run_tests([
    "tests/unit/models/test_order_dao.py",
], "test_order_dao ALONE")
