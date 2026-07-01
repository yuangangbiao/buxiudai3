#!/usr/bin/env python3
"""递归清除 __pycache__ 目录"""
import os, shutil

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
count = 0
for dirpath, dirnames, filenames in os.walk(root):
    if '__pycache__' in dirnames:
        path = os.path.join(dirpath, '__pycache__')
        shutil.rmtree(path, ignore_errors=True)
        count += 1
        print(f'  removed: {path}')
print(f'Cleared {count} __pycache__ directories')
