"""[审计] 昨天任务的水分分析"""
import subprocess
import re

# commit 前 _core.py
r = subprocess.run(['git', 'show', '2599c47d^:mobile_api_ai/dispatch_center/_core.py'], capture_output=True, text=True)
content_before = r.stdout

# commit 后
with open(r'mobile_api_ai\dispatch_center\_core.py', 'r', encoding='utf-8') as f:
    content_after = f.read()

# 数 str(e) 等模式
patterns = [
    (r'str\(e\)', 'str(e)'),
    (r'str\(err\)', 'str(err)'),
    (r'str\(exc\)', 'str(exc)'),
    (r'str\(exception\)', 'str(exception)'),
]
print('=== str() 调用模式统计 ===')
for p, label in patterns:
    before = len(re.findall(p, content_before))
    after = len(re.findall(p, content_after))
    print(f'  {label}: 前 {before} -> 后 {after}')

# 看 commit 中提及 92 处的说法是否对应
print()
print('=== commit 文档声称 ===')
print('"批量替换 92 处 str(e) → 服务器内部错误"')
print()

# 看 P2-7 报工超量代码实际在哪
print('=== P2-7 报工超量拦截 ===')
print('grep [P2-7] 出现位置:')
import os
for root, dirs, files in os.walk('.'):
    if '.git' in root or 'docs' in root:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        full = os.path.join(root, f)
        try:
            with open(full, 'r', encoding='utf-8') as fp:
                for i, line in enumerate(fp, 1):
                    if 'P2-7' in line and '\"' not in line and not line.strip().startswith('#'):
                        print(f'  {full}:{i}: {line.strip()[:80]}')
        except Exception:
            pass