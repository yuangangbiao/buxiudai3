"""二分查找测试污染源"""
import sys
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0')

import subprocess

PYTHON = r"C:\Users\lenovo\AppData\Local\Python\bin\python.exe"
ROOT = r"d:\yuan\不锈钢网带跟单3.0"

def run_pytest(test_filter, label):
    cmd = [
        PYTHON, '-m', 'pytest',
        'tests/unit/utils/test_validators.py::test_required_raises_on_none',
        '-xvs', '--tb=short', '-p', 'no:cacheprovider',
        test_filter,
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    passed = 'PASSED' in result.stdout
    print(f"  {label}: {'PASS' if passed else 'FAIL'}")
    return passed

print("=== 二分查找污染源 ===")
# 测试前半部分
run_pytest('--ignore=tests/unit/utils/test_trace_complete.py',
           '不含 test_trace_complete.py')
run_pytest('--ignore=tests/unit/utils/test_settings_manager_complete.py',
           '不含 test_settings_manager_complete.py')
run_pytest('--ignore=tests/unit/utils/test_sprint30_utils.py',
           '不含 test_sprint30_utils.py')
run_pytest('--ignore=tests/unit/utils/test_query_cache.py',
           '不含 test_query_cache.py')
run_pytest('--ignore=tests/unit/utils/test_query_cache_complete.py',
           '不含 test_query_cache_complete.py')
