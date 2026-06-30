# -*- coding: utf-8 -*-
with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
# Check for any weird bytes in lines 7891-7905
for i in range(7890, 7905):
    line = lines[i]
    decoded_ok = True
    try:
        decoded = line.decode('utf-8')
    except:
        decoded_ok = False
        decoded = line.decode('utf-8', errors='replace')
    # Check for non-ASCII bytes
    non_ascii = [(j, hex(b)) for j, b in enumerate(line) if b > 127]
    # Check for tab
    has_tab = b'\t' in line
    print(f"L{i+1}: len={len(line)}, ascii_ok={decoded_ok}, tab={has_tab}, non_ascii={non_ascii[:3]}")
    print(f"  {repr(line[:60])}")
