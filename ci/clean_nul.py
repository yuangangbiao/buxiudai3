# -*- coding: utf-8 -*-
import os, sys
ROOT = r'd:\yuan\不锈钢网带跟单3.0'
nul_count = 0
for root, dirs, files in os.walk(ROOT):
    if 'archive' in root or '.git' in root or '__pycache__' in root:
        continue
    for f in files:
        if f == 'nul':
            path = os.path.join(root, f)
            try:
                os.remove(path)
                nul_count += 1
            except Exception as e:
                print(f'无法删除 {path}: {e}', file=sys.stderr)
print(f'已删除 {nul_count} 个 nul 文件')
