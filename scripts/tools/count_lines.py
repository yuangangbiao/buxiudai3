import os
os.chdir(r'd:\yuan\不锈钢网带跟单3.0')

with open('scripts/tools/.head_core.py', 'rb') as f:
    content = f.read()
print(f'HEAD _core.py: {content.count(bytes([10]))} lines')

with open('mobile_api_ai/dispatch_center/_core.py', 'rb') as f:
    cur = f.read()
print(f'current _core.py: {cur.count(bytes([10]))} lines')

# ASCII-safe byte strings
print(f'api_get_alert_rules count: {cur.count(b"def api_get_alert_rules")}')
print(f'Part 20 count: {cur.count(b"Part 20")}')