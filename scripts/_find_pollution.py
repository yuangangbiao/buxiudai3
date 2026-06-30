"""精确找污染文件 - 显示完整结果"""
import subprocess
PYTHON = r"C:\Users\lenovo\AppData\Local\Python\bin\python.exe"
ROOT = r"d:\yuan\不锈钢网带跟单3.0"

# 收集测试顺序
r = subprocess.run(
    [PYTHON, '-m', 'pytest', '--collect-only', 'tests/unit', '-p', 'no:cacheprovider',
     '--ignore=tests/unit/test_event_bus_factory.py'],
    cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace'
)

lines = r.stdout.splitlines()
test_files = []
for l in lines:
    if '<Module' in l:
        fname = l.split('(')[0].strip().replace('<Module ', '').replace('>', '').strip()
        if fname.endswith('.py'):
            if not test_files or test_files[-1] != fname:
                test_files.append(fname)

v_idx = next((i for i, f in enumerate(test_files) if 'test_validators.py' in f), None)
test_set = test_files[max(0, v_idx-50):v_idx+1]

# 恢复原始 test_validators.py 并添加 debug 测试
test_file = ROOT + r"\tests\unit\utils\test_validators.py"
backup_orig = test_file + '.bak'
import shutil, os
if os.path.exists(backup_orig):
    shutil.copy(backup_orig, test_file)
    print("已恢复原始 test_validators.py")

with open(test_file, 'r', encoding='utf-8') as f:
    content = f.read()

debug_tests = r'''
def test_DEBUG_pytest_raises_match():
    import pytest
    from core.exceptions import ValidationException
    from utils.validators import CommonValidators
    with pytest.raises(ValidationException, match="不能为空"):
        CommonValidators.required(None, "customer_name")
'''
new_content = content + debug_tests

with open(test_file, 'w', encoding='utf-8') as f:
    f.write(new_content)

# 运行
cmd = [PYTHON, '-m', 'pytest'] + test_set + [
    'tests/unit/utils/test_validators.py::test_DEBUG_pytest_raises_match',
    '-xvs', '--tb=short', '-p', 'no:cacheprovider',
]
print(f"运行 {len(cmd)-3} 个文件...")
r2 = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')

# 恢复
shutil.copy(backup_orig, test_file)

# 找关键结果
out_lines = r2.stdout.splitlines()
for line in out_lines:
    if 'DEBUG' in line or 'FAILED' in line or 'PASSED' in line:
        print(f"  {line.strip()}")
print(f"\nEXIT: {r2.returncode}")

# 找哪个测试失败
if r2.returncode != 0:
    print("\n失败详情:")
    for i, line in enumerate(out_lines):
        if 'FAILED' in line:
            print(f"  {line.strip()}")
            # 打印后面几行
            for j in range(i+1, min(i+5, len(out_lines))):
                print(f"    {out_lines[j]}")
