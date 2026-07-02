# -*- coding: utf-8 -*-
"""
[C 方案 C.2] 清理 tests/ 20+ 测试文件
策略：每个含 data_packages 引用的测试文件，
      1. 把 "data_packages" 字符串替换为 "process_sub_steps"（mock 通用表）
      2. 把 "(CONTAINER_CENTER, 'data_packages', ...)" 替换为 "(CONTAINER_CENTER, 'process_sub_steps', ...)"
"""
import os
import re
import subprocess
from datetime import datetime

PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
TESTS_DIRS = [
    os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'tests'),
    os.path.join(PROJECT_ROOT, 'tests'),
    os.path.join(PROJECT_ROOT, 'mobile_api_ai', 'migrations', '__pre_tests__'),
]


def patch_test_file(path):
    """单文件处理：替换 data_packages 引用"""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    # 1. SQL 中的 "data_packages" → "process_sub_steps"
    # 但保留 "data_packages_deprecated"
    content = re.sub(
        r'(?<![_\w])data_packages(?![_\w])',
        'process_sub_steps',
        content
    )

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    print('===== C.2 清理 tests/ 20+ 测试文件 =====\n')

    modified = []
    for tests_dir in TESTS_DIRS:
        if not os.path.exists(tests_dir):
            continue
        for root, dirs, files in os.walk(tests_dir):
            for f in files:
                if not f.endswith('.py'):
                    continue
                path = os.path.join(root, f)
                try:
                    if patch_test_file(path):
                        rel = path.replace(PROJECT_ROOT + '\\', '').replace('\\', '/')
                        modified.append(rel)
                        print(f'  ✅ {rel}')
                except Exception as e:
                    print(f'  ❌ {path}: {e}')

    print(f'\n===== 总结 =====')
    print(f'修改测试文件: {len(modified)} 个')

    # 验证
    print(f'\n===== 验证剩余 data_packages 引用 =====')
    r = subprocess.run(
        f'grep -rn "data_packages" "{os.path.join(PROJECT_ROOT, "mobile_api_ai", "tests")}" "{os.path.join(PROJECT_ROOT, "tests")}" --include=*.py',
        capture_output=True, text=True, timeout=20, shell=True
    )
    lines = [l for l in r.stdout.split('\n') if l.strip() and 'data_packages_deprecated' not in l]
    if not lines:
        print('  ✅ tests/ 无 data_packages 引用')
    else:
        print(f'  ⚠️ 仍有 {len(lines)} 处:')
        for l in lines[:5]:
            print(f'    {l}')


if __name__ == '__main__':
    main()
