import os
import re
from pathlib import Path

os.chdir(r'D:\yuan\不锈钢网带跟单3.0\mobile_api_ai')

ROUTES = []
BP_PREFIXES = {}
for py_file in Path('.').rglob('*.py'):
    pstr = str(py_file).replace('\\', '/')
    if '_archive' in pstr or '/tests/' in pstr:
        continue
    try:
        content = py_file.read_text(encoding='utf-8')
    except Exception:
        continue
    for m in re.finditer(r'Blueprint\(\s*[\'"](\w+)[\'"].*?url_prefix\s*=\s*[\'"]([^\'"]+)[\'"]', content, re.DOTALL):
        BP_PREFIXES[m.group(1)] = m.group(2)
    pattern = r'@(\w+)\.route\(\s*[\'"]([^\'"]+)[\'"]'
    for m in re.finditer(pattern, content):
        bp_name = m.group(1)
        path = m.group(2)
        line = content[:m.start()].count('\n') + 1
        prefix = BP_PREFIXES.get(bp_name, '')
        full_path = prefix + path if prefix else path
        ROUTES.append((full_path, bp_name, pstr, line))

unique_paths = sorted(set(r[0] for r in ROUTES))
print(f'总路由数: {len(unique_paths)}')

# 找 dispatch-center 相关路由
dispatch_routes = [p for p in unique_paths if 'dispatch-center' in p]
print(f'dispatch-center 路由数: {len(dispatch_routes)}')
for r in dispatch_routes[:10]:
    print(f'  {r}')
print()

# 看具体路径格式
print('=== 实际找到的 /alerts* 路径 ===')
for r in unique_paths:
    if '/alerts' in r:
        print(f'  {repr(r)}')