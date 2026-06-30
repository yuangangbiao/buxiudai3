"""[扫描] cursor.execute 中的 SQL"""
import os
import re

print('=== cursor.execute 中的 UPDATE/INSERT/DELETE ===')
for root, dirs, files in os.walk('.'):
    if '.git' in root or '.venv' in root:
        continue
    if 'scripts/archive' in root:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        full = os.path.join(root, f)
        try:
            with open(full, 'r', encoding='utf-8') as fp:
                for i, line in enumerate(fp, 1):
                    s = line.strip()
                    # cursor.execute / cur.execute
                    if 'execute(' in s and ('UPDATE' in s or 'INSERT' in s or 'DELETE' in s):
                        if not s.startswith('#'):
                            print(f'  {full}:{i}: {s[:120]}')
        except Exception:
            pass

print()
print('=== container_center_v5.py 的 SQL ===')
for path in ['mobile_api_ai/container_center_v5.py', 'container_center_v5.py']:
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        for i, line in enumerate(content.split('\n'), 1):
            s = line.strip()
            if 'execute(' in s and len(s) > 10:
                print(f'  {path}:{i}: {s[:120]}')