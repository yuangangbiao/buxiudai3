# -*- coding: utf-8 -*-
with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

state = 0
for i in range(8824, 8850):
    cnt = lines[i].count(b'"""')
    if cnt > 0 or True:
        decoded = lines[i].decode('utf-8', errors='replace')
        print(f"L{i+1} (cnt={cnt}, state_before={state}): {repr(decoded[:50])}")
        for k in range(cnt):
            if state == 0:
                state = 1
                print(f"  -> OPEN at iteration {k+1}")
            else:
                state = 0
                print(f"  -> CLOSE at iteration {k+1}")
        print(f"  state_after={state}")
