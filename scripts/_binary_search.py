"""二分查找: 找到哪个测试文件污染了 validators"""
import subprocess
PYTHON = r"C:\Users\lenovo\AppData\Local\Python\bin\python.exe"
ROOT = r"d:\yuan\不锈钢网带跟单3.0"

# 收集所有测试文件的顺序
result_collect = subprocess.run(
    [PYTHON, '-m', 'pytest', '--collect-only', '-q', 'tests/unit',
     '--ignore=tests/unit/test_event_bus_factory.py'],
    cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace'
)
test_lines = [l.strip() for l in result_collect.stdout.splitlines() if '::test_' in l]
all_files_ordered = []
for t in test_lines:
    f = t.split('::')[0]
    if not all_files_ordered or all_files_ordered[-1] != f:
        all_files_ordered.append(f)

# 找 test_validators.py 位置
v_idx = next((i for i, t in enumerate(test_lines) if 'test_validators.py::' in t), None)
if v_idx is None:
    print("未找到 test_validators.py")
    exit(1)

# 找 test_validators.py 之前的所有文件
files_before = []
for i, t in enumerate(test_lines):
    if 'test_validators.py::' in t:
        break
    f = t.split('::')[0]
    if not files_before or files_before[-1] != f:
        files_before.append(f)

print(f"test_validators.py 之前有 {len(files_before)} 个文件:")
for f in files_before[-5:]:
    print(f"  {f}")

# 二分搜索: 先测试后半部分
mid = len(files_before) // 2
test_files = files_before[mid:]  # 后半部分

print(f"\n测试后半部分 ({len(test_files)} 个文件) + validators...")
cmd = [
    PYTHON, '-m', 'pytest',
] + test_files + [
    'tests/unit/utils/test_validators.py::test_required_passes_non_empty_string',
    'tests/unit/utils/test_validators.py::test_required_raises_on_none',
    '-xvs', '--tb=short', '-p', 'no:cacheprovider',
]
result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')

# 找结果
for line in result.stdout.splitlines():
    if 'test_required_raises_on_none' in line or 'test_required_passes' in line:
        print(f"  {line.strip()}")
