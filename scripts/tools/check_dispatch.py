"""检查 dispatch_center.py：语法、括号匹配、硬编码"""
import ast
import re
import sys

path = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\dispatch_center.py'

with open(path, 'r', encoding='utf-8') as f:
    source = f.read()
lines = source.split('\n')
print(f'总行数: {len(lines)}')

# 1
print('\n=== 1. 语法检查 ===')
try:
    ast.parse(source)
    print('  OK')
except SyntaxError as e:
    print(f'  FAIL: {e}')
    sys.exit(1)

# 2
print('\n=== 2. 括号匹配 ===')
for name, o, c in [('圆括号', '(', ')'), ('方括号', '[', ']'), ('花括号', '{', '}')]:
    diff = source.count(o) - source.count(c)
    print(f'  {name}: {o}={source.count(o)}  {c}={source.count(c)}  diff={diff}')
print('  OK' if source.count('(')==source.count(')') and source.count('[')==source.count(']') and source.count('{')==source.count('}') else '  FAIL')

# 3
print('\n=== 3. 敏感信息硬编码 ===')
found = False
for label, pat in [('password', r'["\'](?:password|passwd|pwd)["\']\s*[:=]\s*["\']'),
                    ('api_key', r'["\'](?:api_key|apikey)["\']\s*[:=]\s*["\']'),
                    ('secret', r'["\'](?:secret|SECRET)["\']\s*[:=]\s*["\']'),
                    ('token', r'["\'](?:token|TOKEN|access_token)["\']\s*[:=]\s*["\']')]:
    for i, line in enumerate(lines, 1):
        if re.search(pat, line) and not line.strip().startswith('#'):
            print(f'  [{label}] L{i}: {line.strip()[:80]}')
            found = True
print('  OK' if not found else '  FAIL')

# 4
print('\n=== 4. 硬编码路径检查 ===')
found = False
for i, line in enumerate(lines, 1):
    s = line.strip()
    if s.startswith('#') or 'import' in s:
        continue
    if 'os.path.join' in line and 'BASE_DIR' not in line and 'get_config_path' not in line:
        print(f'  L{i}: {s[:90]}')
        found = True
print('  OK' if not found else '  FAIL')

# 5
print('\n=== 5. print语句检查 ===')
found = False
for i, line in enumerate(lines, 1):
    s = line.strip()
    if s.startswith('#'):
        continue
    if re.match(r'^print\s*\(', s):
        print(f'  L{i}: {s[:80]}')
        found = True
print('  OK' if not found else '  FAIL')

# 6
print('\n=== 6. split - except裸检查 ===')
found = False
for i, line in enumerate(lines, 1):
    s = line.strip()
    if s.startswith('#'):
        continue
    if re.match(r'^except\s*:', s):
        print(f'  L{i}: {s}')
        found = True
print('  OK' if not found else '  FAIL')

# 7 import 区
print('\n=== 7. import区域(前20行) ===')
for i in range(min(20, len(lines))):
    if lines[i].strip():
        print(f'  L{i+1}: {lines[i].rstrip()}')

print('\n=== DONE ===')
