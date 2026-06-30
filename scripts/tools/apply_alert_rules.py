# -*- coding: utf-8 -*-
"""把 alert_rules 块追加到 _core.py 末尾，生成干净的 commit 2 内容"""
import os

os.chdir(r'd:\yuan\不锈钢网带跟单3.0')

with open('mobile_api_ai/dispatch_center/_core.py', 'r', encoding='utf-8') as f:
    core = f.read()

with open('scripts/tools/.alert_rules_block.py', 'r', encoding='utf-8') as f:
    block = f.read()

# 确保 core 以单换行结尾，然后追加 block
if not core.endswith('\n'):
    core += '\n'
# block 末尾已有 1 个换行，再加 1 个确保后续修改不会粘连
core += block
if not core.endswith('\n'):
    core += '\n'

with open('mobile_api_ai/dispatch_center/_core.py', 'w', encoding='utf-8') as f:
    f.write(core)

print(f'_core.py 写完，新行数: {len(core.splitlines())}')