import os
os.chdir(r'd:\yuan\不锈钢网带跟单3.0')

# 读 HEAD 版本 (已经在 .head_core.py)
with open('scripts/tools/.head_core.py', 'rb') as f:
    head_content = f.read()

# 读 alert_rules 块
with open('scripts/tools/.alert_rules_block.py', 'rb') as f:
    block = f.read()

# 拼接：HEAD + 空行（如果需要）+ alert_rules 块
# 检查 HEAD 是否以 \n 结尾
if not head_content.endswith(b'\n'):
    head_content += b'\n'

# alert_rules 块 53 行，第一行是 "# ════..." 注释
# 在块前面加一个空行作为分隔
new_content = head_content + b'\n' + block

# 验证：alert_rules 只出现 1 次
print(f'new content alert_rules count: {new_content.count(b"def api_get_alert_rules")}')
print(f'new content Part 20 count: {new_content.count(b"Part 20")}')

# 写入 _core.py
with open('mobile_api_ai/dispatch_center/_core.py', 'wb') as f:
    f.write(new_content)

# 验证
with open('mobile_api_ai/dispatch_center/_core.py', 'rb') as f:
    check = f.read()
print(f'written _core.py: {check.count(bytes([10]))} lines')
print(f'written api_get_alert_rules count: {check.count(b"def api_get_alert_rules")}')