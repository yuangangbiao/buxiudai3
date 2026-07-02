# -*- coding: utf-8 -*-
import os, re
PROJECT_ROOT = os.getenv('GITHUB_WORKSPACE', os.getcwd())
EXCLUDE = ['archive', '__pycache__', '.pyc', 'final_verify', 'find_real_sql']
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
        for i, line in enumerate(lines, 1):
            if 'data_packages' not in line or 'data_packages_deprecated' in line or 'data_packages_split' in line:
                continue
            # 检查是否真的 SQL（不是注释或纯字符串）
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if '"""' in line[:30] or "'''" in line[:30]:
                continue
            # 找 SQL 关键词
            if re.search(r'(SELECT|FROM|UPDATE|INSERT|DELETE|cur\.execute|cursor\.execute)', line, re.I):
                print(f'{rel}:{i} {stripped[:100]}')
