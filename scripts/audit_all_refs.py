"""[审计 v2] 全部 from-imports（生产+脚本）"""
import os

print('=== 全部残留（含 scripts）===')
for root, dirs, files in os.walk('.'):
    if '.git' in root:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        full = os.path.join(root, f)
        try:
            with open(full, 'r', encoding='utf-8') as fp:
                lines = fp.readlines()
            in_docstring = False
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                        in_docstring = not in_docstring
                    continue
                if in_docstring:
                    continue
                if (stripped.startswith('from desktop_container_integration import')
                    and not stripped.startswith('#')
                    and 'desktop_container_integration.py' not in full):
                    print(f'  {full}:{i}: {stripped[:80]}')
        except Exception:
            pass

print()
print('=== 全部 DesktopContainerIntegration() 实例化 ===')
for root, dirs, files in os.walk('.'):
    if '.git' in root:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        full = os.path.join(root, f)
        try:
            with open(full, 'r', encoding='utf-8') as fp:
                for i, line in enumerate(fp, 1):
                    if 'DesktopContainerIntegration()' in line and 'desktop_container_integration.py' not in full:
                        print(f'  {full}:{i}: {line.strip()[:80]}')
        except Exception:
            pass