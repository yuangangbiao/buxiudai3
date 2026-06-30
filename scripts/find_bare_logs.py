# -*- coding: utf-8 -*-
"""[Q-B7] 查找裸异常日志"""
import re
import sys

target = sys.argv[1] if len(sys.argv) > 1 else r'mobile_api_ai\dispatch_center\_core.py'

with open(target, 'r', encoding='utf-8') as f:
    content = f.read()

# 匹配 logger.error(f'...{e}') 或 logger.error(f"..{e}")
pattern = re.compile(r"logger\.(error|critical)\(f['\"]([^'\"]*)\{e\}[^'\"]*['\"]\)")
matches = list(pattern.finditer(content))
print(f'找到 {len(matches)} 处裸异常日志')
for i, m in enumerate(matches[:20]):
    line_no = content[:m.start()].count('\n') + 1
    snippet = m.group(0)[:90]
    print(f'{i+1}. L{line_no}: {snippet}')
