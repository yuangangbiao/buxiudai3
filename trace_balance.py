# -*- coding: utf-8 -*-
with open(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center\_core.py', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')

state = 0
for i in range(0, 50):
    cnt = lines[i].count(b'"""')
    if cnt > 0:
        decoded = lines[i].decode('utf-8', errors='replace')
        print(f"L{i+1} (dq={cnt}, state={state}): {repr(decoded[:40])}")
        for k in range(cnt):
            old_state = state
            if state == 0:
                state = 1
            else:
                state = 0
            print(f"  -> after dq {k+1}: state {old_state} -> {state}")
    if i == 38:
        print(f"... (skipping to line 8459)")
    if i > 8458:
        cnt = lines[i].count(b'"""')
        if cnt > 0:
            decoded = lines[i].decode('utf-8', errors='replace')
            print(f"L{i+1} (dq={cnt}, state={state}): {repr(decoded[:40])}")
            for k in range(cnt):
                old_state = state
                if state == 0:
                    state = 1
                else:
                    state = 0
                print(f"  -> after dq {k+1}: state {old_state} -> {state}")
        if i > 8475:
            break
