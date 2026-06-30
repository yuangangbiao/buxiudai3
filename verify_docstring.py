# -*- coding: utf-8 -*-
with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

# Proper triple-quote balance tracking
# state=0: outside string, state=1: inside string
state = 0
first_unclosed = None
for i, line in enumerate(lines):
    cnt = line.count(b'"""')
    for k in range(cnt):
        if state == 0:
            state = 1  # opening
        else:
            state = 0  # closing
    if state == 1 and first_unclosed is None:
        first_unclosed = i + 1
        decoded = line.decode('utf-8', errors='replace')
        print(f"First unclosed at line {i+1}: {repr(decoded[:60])}")
        # Show next 5 lines
        for j in range(i+1, min(i+6, len(lines))):
            d2 = lines[j].decode('utf-8', errors='replace')
            print(f"  L{j+1}: {repr(d2[:60])}")

print(f"\nFinal state: {'OPEN' if state == 1 else 'CLOSED'}")
if first_unclosed is None:
    print("All docstrings are properly balanced!")
