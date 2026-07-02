# -*- coding: utf-8 -*-
"""[v3.6 T9.1] 列出所有 data_packages 引用的文件"""
import os
import re

PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
MOBILE_API = os.path.join(PROJECT_ROOT, 'mobile_api_ai')

# 排除已处理的
EXCLUDE_PATTERNS = [
    'data_type_router', 'exception_handler', 'check_stage',
    'data_packages_deprecated', 'data_packages_split',
    'fix_v3_6_4fields', 'test_t1_routing', 'test_t2b_auth',
    'list_data_packages', 'run_stage_1_ddl',
    '.pyc', '__pycache__',
]

results = {}

# 1. mobile_api_ai 所有 .py
for root, dirs, files in os.walk(MOBILE_API):
    # 排除 __pycache__
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        rel = path.replace(PROJECT_ROOT + '\\', '').replace('\\', '/')
        if any(p in rel for p in EXCLUDE_PATTERNS):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as fp:
                content = fp.read()
        except Exception:
            continue
        if 'data_packages' not in content:
            continue
        # 找出含 data_packages 的行
        lines = content.split('\n')
        data_pkg_lines = []
        for i, line in enumerate(lines, 1):
            if 'data_packages' in line and 'data_packages_deprecated' not in line:
                data_pkg_lines.append(f'   L{i}: {line.strip()[:100]}')
        if data_pkg_lines:
            results[rel] = data_pkg_lines

# 2. scripts 和 tests
for sub in ['scripts', 'tests', 'stats_smart_sheet', 'services']:
    path = os.path.join(PROJECT_ROOT, sub)
    if not os.path.exists(path):
        continue
    for root, dirs, files in os.walk(path):
        for f in files:
            if not f.endswith('.py'):
                continue
            full = os.path.join(root, f)
            rel = full.replace(PROJECT_ROOT + '\\', '').replace('\\', '/')
            if any(p in rel for p in EXCLUDE_PATTERNS):
                continue
            try:
                with open(full, 'r', encoding='utf-8') as fp:
                    content = fp.read()
            except Exception:
                continue
            if 'data_packages' not in content:
                continue
            lines = content.split('\n')
            data_pkg_lines = []
            for i, line in enumerate(lines, 1):
                if 'data_packages' in line and 'data_packages_deprecated' not in line:
                    data_pkg_lines.append(f'   L{i}: {line.strip()[:100]}')
            if data_pkg_lines:
                results[rel] = data_pkg_lines

print(f'共发现 {len(results)} 个文件含 data_packages 引用：\n')
for f, lines in sorted(results.items()):
    print(f'📄 {f}')
    for l in lines[:5]:
        print(l)
    if len(lines) > 5:
        print(f'   ...还有 {len(lines) - 5} 行')
    print()

# 输出到文件
with open(os.path.join(PROJECT_ROOT, 'ci', 'data_packages_inventory.txt'), 'w', encoding='utf-8') as f:
    f.write(f'共 {len(results)} 个文件\n\n')
    for path, lines in sorted(results.items()):
        f.write(f'{path}\n')
        for l in lines:
            f.write(f'{l}\n')
        f.write('\n')

print(f'\n清单已保存到 ci/data_packages_inventory.txt')
