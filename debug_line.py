# -*- coding: utf-8 -*-
data = open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'rb').read()
lines = data.split(b'\n')
# Count " occurrences in the file
count = data.count(b'"""')
print(f'Total """ occurrences: {count}')
# Find ALL " patterns
for i, l in enumerate(lines):
    if b'"""' in l:
        print(f'L{i+1}: {repr(l[:50])}')
