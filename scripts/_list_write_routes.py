"""列 5001 写路由 + 5008 蓝图路由"""
import os
import re

print('=== 5001 desktop_web/server.py 写路由 ===')
with open(r'd:\yuan\不锈钢网带跟单3.0\desktop_web\server.py', 'r', encoding='utf-8') as f:
    content = f.read()
# 简单 regex
pat = re.compile(r"@\w+\.route\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?\s*\)")
for m in pat.finditer(content):
    path = m.group(1)
    methods = m.group(2) or 'GET'
    if any(mt in methods.upper() for mt in ['POST', 'PUT', 'DELETE']):
        print(f'  {methods:60s} {path}')

print('\n=== 5008 mobile_api_ai/api/*.py 蓝图路由 ===')
api_dir = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\api'
for fn in sorted(os.listdir(api_dir)):
    if not fn.endswith('.py') or fn == '__init__.py':
        continue
    full = os.path.join(api_dir, fn)
    with open(full, 'r', encoding='utf-8') as fp:
        c = fp.read()
    # 找 prefix
    bp = re.search(r"Blueprint\(\s*['\"]([^'\"]+)['\"]\s*,\s*__name__\s*(?:,\s*url_prefix\s*=\s*['\"]([^'\"]+)['\"])?", c)
    if not bp:
        continue
    name = bp.group(1)
    prefix = bp.group(2) or ''
    # 找路由
    routes = re.findall(r"@bp\.route\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?\s*\)", c)
    if not routes:
        continue
    print(f'\n--- {fn} (name={name}, prefix={prefix}) ---')
    for path, methods in routes:
        m = methods or 'GET'
        print(f'  {m:60s} {prefix}{path}')
