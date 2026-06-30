"""[盘点] 扫描所有 SQL 写入"""
import os
import re

print('=== 所有 SQL 关键字位置 ===')
for root, dirs, files in os.walk('.'):
    if '.git' in root:
        continue
    if 'scripts/archive' in root:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        full = os.path.join(root, f)
        try:
            with open(full, 'r', encoding='utf-8') as fp:
                content = fp.read()
            # 找 INSERT/UPDATE/DELETE 关键字
            for keyword in ['INSERT', 'UPDATE', 'DELETE', 'REPLACE']:
                pattern = r'\b' + keyword + r'\b'
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                if matches and keyword != 'INSERT':  # 排除注释
                    for m in matches[:3]:
                        # 行号
                        line_no = content[:m.start()].count('\n') + 1
                        # 取整行
                        line_start = content.rfind('\n', 0, m.start()) + 1
                        line_end = content.find('\n', m.end())
                        if line_end == -1:
                            line_end = len(content)
                        line = content[line_start:line_end].strip()
                        if line and not line.startswith('#'):
                            print(f'  [{keyword}] {full}:{line_no}: {line[:80]}')
        except Exception:
            pass