#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量语法检查所有 Python 文件（排除云端更新包等备份目录）"""
import os
import sys
import py_compile
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCLUDE_DIRS = {'云端更新包', '云端更新包_v1.0', '云端更新包_v1.1', '云端部署包', '__pycache__', '.git', 'deploy_output'}
EXCLUDE_FILES = {'fix_all.py'}

errors = []
checked = 0

for root, dirs, files in os.walk(BASE_DIR):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for f in files:
        if not f.endswith('.py') or f in EXCLUDE_FILES:
            continue
        filepath = os.path.join(root, f)
        relpath = os.path.relpath(filepath, BASE_DIR)
        checked += 1
        try:
            py_compile.compile(filepath, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append((relpath, str(e)))

print(f'已检查 {checked} 个文件')
if errors:
    print(f'\n发现 {len(errors)} 个语法错误:\n')
    for path, msg in errors:
        print(f'  [{path}]')
        print(f'    {msg}\n')
    sys.exit(1)
else:
    print('全部通过 ✅')
