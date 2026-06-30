"""[v3.7.5] 查找活跃引用"""
import os
from_refs = []
class_refs = []
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
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if 'from desktop_container_integration import' in line and not stripped.startswith('#'):
                    if 'desktop_container_integration.py' not in full:
                        from_refs.append((full, i, line.strip()[:80]))
                if 'DesktopContainerIntegration()' in line and 'desktop_container_integration.py' not in full:
                    class_refs.append((full, i, line.strip()[:80]))
        except Exception:
            pass

print(f'active from-imports: {len(from_refs)}')
for r in from_refs:
    print(f'  {r[0]}:{r[1]}: {r[2]}')
print(f'类实例化: {len(class_refs)}')
for r in class_refs:
    print(f'  {r[0]}:{r[1]}: {r[2]}')