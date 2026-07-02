# -*- coding: utf-8 -*-
import os
ROOT = r'd:\yuan\不锈钢网带跟单3.0'
for root, dirs, files in os.walk(ROOT):
    if 'archive' in root or '.git' in root or '__pycache__' in root:
        continue
    for f in files:
        if f == 'nul' or f.lower() == 'nul':
            path = os.path.join(root, f)
            print(path, 'EXISTS' if os.path.exists(path) else 'MISS')
