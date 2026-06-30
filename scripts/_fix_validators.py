"""
系统化修复 validator 测试文件中的 pytest.raises(match=) 断言
策略: 将 match= 改为显式 assert in str(exc_info.value)
"""
import sys, os, re

ROOT = r'd:\yuan\不锈钢网带跟单3.0'
sys.path.insert(0, ROOT)

def fix_pytest_raises(content, file_path):
    """将 pytest.raises(..., match="pattern") 改为显式断言"""
    changes = 0

    # 匹配模式: with pytest.raises(Exception, match="pattern"):
    # 改为: with pytest.raises(Exception) as exc_info:
    #           ... (原调用)
    #       assert "pattern" in str(exc_info.value)

    # 正则: with pytest.raises(XXX, match="YYY"):\n    ZZZ
    pattern = re.compile(
        r'with pytest\.raises\(([^)]+),\s*match="([^"]+)"\):\n(.+?)(?=\n    |\n\n|\nclass |\ndef |\Z)',
        re.DOTALL
    )

    def replacer(m):
        nonlocal changes
        exc_type = m.group(1).strip()
        match_pattern = m.group(2)
        code_block = m.group(3).strip()

        # 提取最后一行（调用语句）
        lines = code_block.split('\n')
        last_call = lines[-1].strip()
        leading = '\n    '.join(lines[:-1])

        # 构建新代码
        new_code = f'with pytest.raises({exc_type}) as exc_info:\n'
        new_code += f'        {last_call}\n'
        new_code += f'    assert "{match_pattern}" in str(exc_info.value), \\\n'
        new_code += f'        f"Expected \\\'{match_pattern}\\\' in \\\'{{exc_info.value}}\\\'"'
        if leading:
            new_code = leading + '\n' + new_code

        changes += 1
        return new_code

    new_content = pattern.sub(replacer, content)

    if changes > 0:
        print(f"  {file_path}: 修复 {changes} 处 match= 断言")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    else:
        print(f"  {file_path}: 无需修复")

    return changes

files_to_fix = [
    os.path.join(ROOT, 'tests/unit/utils/test_validators.py'),
    os.path.join(ROOT, 'tests/unit/utils/test_validators_full.py'),
    os.path.join(ROOT, 'tests/unit/utils/test_validators_complete.py'),
]

total = 0
for f in files_to_fix:
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as fp:
            content = fp.read()
        total += fix_pytest_raises(content, f)
    else:
        print(f"  {f}: 文件不存在")

print(f"\n共修复 {total} 处")
