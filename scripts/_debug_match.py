"""精确测试 pytest.raises 的 match 行为"""
import subprocess
PYTHON = r"C:\Users\lenovo\AppData\Local\Python\bin\python.exe"
ROOT = r"d:\yuan\不锈钢网带跟单3.0"

# 在 test_validators.py 中临时添加测试
test_file = ROOT + r"\tests\unit\utils\test_validators.py"
backup_file = test_file + '.bak_debug2'

import shutil
shutil.copy(test_file, backup_file)

with open(test_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加两个测试: 一个用 pytest.raises(match=), 一个用显式 assert
debug_tests = r'''

def test_DEBUG_pytest_raises_match():
    """测试 pytest.raises(match=) 是否工作"""
    import pytest
    from core.exceptions import ValidationException
    from utils.validators import CommonValidators
    with pytest.raises(ValidationException, match="不能为空"):
        CommonValidators.required(None, "customer_name")

def test_DEBUG_explicit_assert():
    """测试显式 assert 是否工作"""
    import pytest
    from core.exceptions import ValidationException
    from utils.validators import CommonValidators
    with pytest.raises(ValidationException) as exc_info:
        CommonValidators.required(None, "customer_name")
    assert "不能为空" in str(exc_info.value)
'''

new_content = content + debug_tests

with open(test_file, 'w', encoding='utf-8') as f:
    f.write(new_content)

# 运行两个调试测试
cmd = [PYTHON, '-m', 'pytest',
       'tests/unit/utils/test_validators.py::test_DEBUG_pytest_raises_match',
       'tests/unit/utils/test_validators.py::test_DEBUG_explicit_assert',
       '-xvs', '--tb=short', '-p', 'no:cacheprovider']
result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')

# 恢复原始文件
shutil.copy(backup_file, test_file)

print("=== 测试结果 ===")
for line in result.stdout.splitlines():
    if 'PASSED' in line or 'FAILED' in line or 'test_DEBUG' in line:
        print(line.strip())
print("\nEXIT:", result.returncode)
print("\n=== 尾部 30 行 ===")
for line in result.stdout.splitlines()[-30:]:
    print(line)
