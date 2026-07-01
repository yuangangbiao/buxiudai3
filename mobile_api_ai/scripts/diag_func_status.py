# -*- coding: utf-8 -*-
"""完整扫描：侧边栏链接 vs 已注册路由，找出未实现的功能"""
import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(r'd:\yuan\不锈钢网带跟单3.0\.env', override=True)
sys.path.insert(0, r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai')
import logging
logging.disable(logging.CRITICAL)
import inventory_api_server
app = inventory_api_server.app

# 已注册路由
registered = set()
for rule in app.url_map.iter_rules():
    if rule.rule.startswith('/inventory'):
        registered.add(rule.rule)

# 侧边栏链接
base = Path(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\inventory_web\templates\inventory\base.html')
text = base.read_text(encoding='utf-8')
sidebar_links = re.findall(r'href="(/inventory[^"]+)"', text)
sidebar_set = set(sidebar_links)

# 模板中调用的 API 端点
template_files = list((Path(r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\inventory_web\templates')).rglob('*.html'))
called_apis = set()
for tf in template_files:
    t = tf.read_text(encoding='utf-8', errors='replace')
    for m in re.finditer(r"['\"](/inventory/api/[^'\"]+)['\"]", t):
        called_apis.add(m.group(1))
    for m in re.finditer(r"fetch\(['\"]([^'\"]+)['\"]", t):
        u = m.group(1)
        if u.startswith('/'):
            called_apis.add(u)

# 扫描结果
lines = ['=== 库存系统功能实现状态 ===', '']
lines.append('【已实现】（路由存在）:')
for r in sorted(registered):
    if 'GET' in app.url_map._rules_by_endpoint.get(r.replace('/', '.'), []):
        pass
    lines.append(f'  ✅ {r}')

lines.append('')
lines.append('【侧边栏链接但 404】（未实现的页面）:')
for s in sorted(sidebar_set - registered):
    lines.append(f'  ❌ {s}')

lines.append('')
lines.append('【模板调用但 404 的 API 端点】:')
for a in sorted(called_apis - registered):
    lines.append(f'  ❌ {a}')

text = '\n'.join(lines)
Path(r'd:\yuan\func_status.txt').write_text(text, encoding='utf-8')
print(text)
