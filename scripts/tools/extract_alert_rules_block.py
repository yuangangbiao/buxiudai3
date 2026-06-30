# -*- coding: utf-8 -*-
"""提取 _core.py L9000-9052 (alert_rules 部分) 到临时文件"""
import os

os.chdir(r'd:\yuan\不锈钢网带跟单3.0')
with open('mobile_api_ai/dispatch_center/_core.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f'总行数: {len(lines)}')

# 提取 L9000-9052 (1-indexed -> 0-indexed 8999-9051)
start = 8999  # L9000 - 1
end = 9052    # L9052
block = lines[start:end]
print(f'提取 L{start+1}-{end}: {len(block)} 行')
print('首 3 行:')
for l in block[:3]:
    print(f'  {l.rstrip()}')
print('末 3 行:')
for l in block[-3:]:
    print(f'  {l.rstrip()}')

with open('scripts/tools/.alert_rules_block.py', 'w', encoding='utf-8') as f:
    f.writelines(block)

print(f'已写入 scripts/tools/.alert_rules_block.py')