# -*- coding: utf-8 -*-
import os
PROJECT_ROOT = r'd:\yuan\不锈钢网带跟单3.0'
EXCLUDE = ['archive', '__pycache__', '.pyc', 'data_packages_inventory',
           'data_type_router', 'check_data_packages', 'find_data_packages',
           'split_data_packages', 'data_packages_split',
           'data_packages_deprecated', 'list_data_packages', 'final_verify']
results = {}
for root, dirs, files in os.walk(PROJECT_ROOT):
    dirs[:] = [d for d in dirs if d not in ('archive', '__pycache__', '.git', 'node_modules', '.trae', '.workbuddy')]
    for f in files:
        if not f.endswith('.py'):
            continue
        path = os.path.join(root, f)
        rel = path.replace(PROJECT_ROOT + '\\', '').replace('\\', '/')
        if any(p in rel for p in EXCLUDE):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as fp:
                content = fp.read()
        except Exception:
            continue
        lines = content.split('\n')
        bad = []
        for i, line in enumerate(lines, 1):
            if 'data_packages' in line and 'data_packages_deprecated' not in line and 'data_packages_split' not in line:
                bad.append((i, line.strip()[:80]))
        if bad:
            results[rel] = bad
print(f'总剩余: {len(results)} 个文件')
for f in sorted(results.keys()):
    print(f'  {f}')
