# -*- coding: utf-8 -*-
"""验证步骤1-4：编译检查"""
import py_compile

files = [
    ('sync/event_bus.py', 'event_bus.py'),
    ('sync/sync_log.py', 'sync_log.py'),
    ('sync/init.py', 'init.py'),
    ('app.py', 'app.py'),
]

for fpath, fname in files:
    try:
        py_compile.compile(fpath, doraise=True)
        print(f'[OK] {fname} - 编译通过')
    except py_compile.PyCompileError as e:
        print(f'[FAIL] {fname} - 编译错误: {e}')
