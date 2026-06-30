# -*- coding: utf-8 -*-
with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

for i, line in enumerate(lines):
    if b'\xef\xbc\x8c' in line or b'\xef\xbc\x9a' in line:
        try:
            decoded = line.decode('utf-8')
        except:
            decoded = line.decode('utf-8', errors='replace')
        print(f"L{i+1}: {repr(decoded[:80])}")
