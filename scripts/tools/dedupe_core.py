import os
os.chdir(r'd:\yuan\不锈钢网带跟单3.0')

with open('mobile_api_ai/dispatch_center/_core.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f'before: {len(lines)} lines')
# 截断到 L9053 (索引 9052)
truncated = lines[:9053]
print(f'after: {len(truncated)} lines')

with open('mobile_api_ai/dispatch_center/_core.py', 'w', encoding='utf-8') as f:
    f.writelines(truncated)

# 验证
with open('mobile_api_ai/dispatch_center/_core.py', 'rb') as f:
    check = f.read()
print(f'alert_rules count: {check.count(b"def api_get_alert_rules")}')
print(f'Part 20 count: {check.count(b"Part 20")}')