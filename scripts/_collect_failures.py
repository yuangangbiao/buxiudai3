"""从完整测试输出中提取所有失败信息"""
import re

# 读取测试输出
with open(r'd:\yuan\不锈钢网带跟单3.0\scripts\_test_root_unit.txt', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

lines = content.splitlines()

# 找所有 FAILED 行
failed_tests = []
for i, line in enumerate(lines):
    if line.strip().startswith('FAILED '):
        failed_tests.append({
            'line': i,
            'text': line.strip(),
            'next_lines': [lines[j] if j < len(lines) else '' for j in range(i+1, min(i+4, len(lines)))]
        })

# 找所有 ERROR 行
error_tests = []
for i, line in enumerate(lines):
    if line.strip().startswith('ERROR '):
        error_tests.append({
            'line': i,
            'text': line.strip(),
        })

print(f"=== 131 FAILED 测试 ===")
for t in failed_tests:
    print(f"\n  {t['text']}")
    for nl in t['next_lines']:
        if nl.strip():
            print(f"    {nl.strip()}")

print(f"\n=== 12 ERROR 测试 ===")
for t in error_tests:
    print(f"  {t['text']}")
