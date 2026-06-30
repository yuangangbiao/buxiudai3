# -*- coding: utf-8 -*-
with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\templates\dispatch_center.html', encoding='utf-8') as f:
    content = f.read()
lines = content.split('\n')
print(f'Total lines: {len(lines)}')
print(f'Total chars: {len(content)}')
print()
for i, l in enumerate(lines):
    l = l.strip()
    if 'id="tab-' in l or 'switchTab(' in l or ('function' in l and '(' in l and 'load' in l.lower()):
        print(f'L{i+1}: {l[:100]}')
