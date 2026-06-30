# -*- coding: utf-8 -*-
"""[v3.7.2] 审计 /sync/ 路由"""
import re
import os
import sys

sync_routes = []
total_blueprint = 0

for root, dirs, files in os.walk('mobile_api_ai'):
    if '.git' in root:
        continue
    for f in files:
        if not f.endswith('.py'):
            continue
        full = os.path.join(root, f)
        try:
            with open(full, 'r', encoding='utf-8') as fp:
                content = fp.read()
            # 找 /sync/ 路由
            for m in re.finditer(r"['\"](/sync/[^'\"]*)['\"]", content):
                route = m.group(1)
                if route:
                    sync_routes.append((full, route))
            # 找 Blueprint
            for m in re.finditer(r"Blueprint\(['\"](\w+)['\"]", content):
                total_blueprint += 1
        except Exception:
            pass

print(f'找到 {len(sync_routes)} 处 /sync/ 路由')
print(f'找到 {total_blueprint} 个 Blueprint')
print()
print('路由示例：')
for full, route in sync_routes[:20]:
    print(f'  {full}: {route}')
