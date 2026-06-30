# -*- coding: utf-8 -*-
data = open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'rb').read()
lines = data.split(b'\n')
# Check lines 7903-7910
print("Lines 7903-7910 (byte-level):")
for i in range(7902, 7911):
    print(f"L{i+1}: {repr(lines[i][:80])}")
