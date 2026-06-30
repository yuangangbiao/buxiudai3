# -*- coding: utf-8 -*-
with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

state = 0
last_toggle_line = None
for i, line in enumerate(lines):
    cnt = line.count(b'"""')
    if cnt > 0:
        decoded = lines[i].decode('utf-8', errors='replace')
        if 38 <= i <= 42 or i > 8455:
            print(f"L{i+1} (dq={cnt}, state={state}): {repr(decoded[:40])}")
        for k in range(cnt):
            if state == 0:
                state = 1
                last_toggle_line = i + 1
            else:
                state = 0
                last_toggle_line = None
            if (38 <= i <= 42 or i > 8455) and cnt > 0:
                print(f"  -> state now={state}, last_open={last_toggle_line}")

print(f"\nFinal state: {'OPEN' if state == 1 else 'CLOSED'}")
if state == 1:
    print(f"Last unclosed docstring opened at line {last_toggle_line}")
