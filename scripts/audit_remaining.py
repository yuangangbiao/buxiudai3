"""[审计 v2] 查找残留"""
import os

print('=== 残留 from desktop_container_integration import (生产路径) ===')
for root, dirs, files in os.walk('.'):
    if '.git' in root:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        full = os.path.join(root, f)
        # 跳过 scripts 目录（归档脚本）
        if 'scripts' in full:
            continue
        try:
            with open(full, 'r', encoding='utf-8') as fp:
                lines = fp.readlines()
            in_docstring = False
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                # 简单 docstring 检测
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    in_docstring = not in_docstring if stripped.count('"""') == 1 or stripped.count("'''") == 1 else False
                    continue
                if in_docstring:
                    continue
                if (stripped.startswith('from desktop_container_integration import')
                    and not stripped.startswith('#')
                    and 'desktop_container_integration.py' not in full
                    and '旧:' not in stripped):
                    print(f'  {full}:{i}: {stripped[:80]}')
        except Exception:
            pass