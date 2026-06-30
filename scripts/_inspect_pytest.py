"""精确验证: 在 trace_complete 之后运行 validators 前两个测试"""
import subprocess
PYTHON = r"C:\Users\lenovo\AppData\Local\Python\bin\python.exe"
ROOT = r"d:\yuan\不锈钢网带跟单3.0"

# 确认文件已恢复
print("=== 验证文件状态 ===")
import os
content = open(os.path.join(ROOT, 'tests/unit/utils/test_validators.py'), encoding='utf-8').read()
print(f"test_validators.py has test_DEBUG: {'test_DEBUG' in content}")
print(f"test_validators.py has test_required_raises_on_none: {'test_required_raises_on_none' in content}")

# 运行
cmd = [PYTHON, '-m', 'pytest',
       'tests/unit/utils/test_trace_complete.py',
       'tests/unit/utils/test_validators.py::test_required_passes_non_empty_string',
       'tests/unit/utils/test_validators.py::test_required_raises_on_none',
       '-xvs', '--tb=short', '-p', 'no:cacheprovider']
print("\n运行: trace_complete + validators 前2个测试...")
r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')

for line in r.stdout.splitlines():
    if 'test_required' in line or 'PASSED' in line or 'FAILED' in line:
        print(f"  {line.strip()}")
print(f"\nEXIT: {r.returncode}")
if r.returncode != 0:
    print("\n=== 尾部 15 行 ===")
    for line in r.stdout.splitlines()[-15:]:
        print(line)
