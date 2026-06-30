# -*- coding: utf-8 -*-
data = open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'rb').read()
lines = data.split(b'\n')
# Check lines 7873-7880
print("Lines 7874-7882 (byte-level):")
for i in range(7873, 7882):
    print(f"L{i+1}: {repr(lines[i][:50])}")

# Check lines 7889-7895
print("\nLines 7889-7895:")
for i in range(7888, 7895):
    print(f"L{i+1}: {repr(lines[i][:50])}")
