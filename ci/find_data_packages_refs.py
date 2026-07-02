import os
import re

PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())
EXCLUDE = ['archive', '__pycache__', '.pyc', 'data_packages_inventory',
           'data_type_router', 'check_data_packages', 'find_data_packages',
           'split_data_packages', 'data_packages_split',
           'data_packages_deprecated', 'list_data_packages']

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
        # 找含 data_packages 的行（排除 data_packages_deprecated）
        lines = content.split('\n')
        bad = []
        for i, line in enumerate(lines, 1):
            if 'data_packages' in line and 'data_packages_deprecated' not in line and 'data_packages_split' not in line:
                bad.append((i, line.strip()))
        if bad:
            results[rel] = bad

print(f'代码中含 data_packages 引用（不含 _deprecated）的文件: {len(results)} 个\n')
for f, lines in sorted(results.items()):
    print(f'📄 {f}')
    for ln, txt in lines[:5]:
        print(f'   L{ln}: {txt[:100]}')
    if len(lines) > 5:
        print(f'   ...还有 {len(lines) - 5} 行')
    print()
