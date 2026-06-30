# -*- coding: utf-8 -*-
with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for i in range(493, 508):
    line = lines[i]
    leading = len(line) - len(line.lstrip())
    has_tab = b'\t' in line
    leading_repr = repr(line[:leading+4])
    print(f'L{i+1} (leading={leading}, tab={has_tab}): {repr(line[:50])}')
