# -*- coding: utf-8 -*-
with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

balance = 0
for i, line in enumerate(lines):
    cnt = line.count(b'"""')
    for k in range(cnt):
        balance = 1 - balance
    if balance == 1 and not line.startswith(b'#'):
        decoded = line.decode('utf-8', errors='replace')
        if decoded.strip() and decoded.strip() != '"""':
            print(f"L{i+1} FIRST non-comment unclosed: {repr(decoded[:60])}")
            break
