# -*- coding: utf-8 -*-
"""输出 dashboard 关键片段到文件"""
content = open(r'd:\yuan\dashboard_real.html', encoding='utf-8').read()
import re
nums = re.findall(r'>\s*(\d+(?:\.\d+)?)\s*<', content)

from pathlib import Path
out_lines = ['len: ' + str(len(content)), '所有数字: ' + str(nums), '']
# 取 1100-3500 片段（去 emoji）
snippet = content[1100:3500].encode('gbk', errors='replace').decode('gbk', errors='replace')
out_lines.append('=== 1100-3500 ===')
out_lines.append(snippet)
Path(r'd:\yuan\dashboard_snip.txt').write_text('\n'.join(out_lines), encoding='utf-8')
print('OK, len=', len(content))
print('nums:', nums)
