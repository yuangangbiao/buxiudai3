"""验证系统配置 tab 完整集成到调度中心仪表盘"""

import urllib.request
import json

BASE = 'http://127.0.0.1:5000'
all_ok = True

def check(label, ok):
    global all_ok
    if not ok: all_ok = False
    print(f'  [{"OK" if ok else "FAIL"}] {label}')

# 1. HTML 页面
print('--- dispatch_center.html ---')
r = urllib.request.urlopen(f'{BASE}/api/dispatch-center/')
html = r.read().decode('utf-8')

check('sidebar 系统配置', 'system-config' in html)
check('tab-content 系统配置', 'tab-system-config' in html)
check('配置分类侧栏容器', 'config-category-tabs' in html)
check('配置内容区域', 'config-category-content' in html)

# 2. CSS 布局样式
print('--- dispatch_center.css ---')
r2 = urllib.request.urlopen(f'{BASE}/static/css/dispatch_center.css')
css = r2.read().decode('utf-8')

for s in ['config-center-layout', 'config-sidebar', 'config-sidebar-item', 'config-main', 'config-action-bar']:
    check(f'CSS 包含 {s}', s in css)

# 3. JS 新函数
print('--- dispatch_center.js ---')
r3 = urllib.request.urlopen(f'{BASE}/static/js/dispatch_center.js')
js = r3.read().decode('utf-8')

for fn in ['renderConfigCenter', 'saveSystemConfig', 'testSystemConfig',
           'renderCategoryContent', 'renderField', 'collectFormValues']:
    check(f'JS 包含 {fn}', fn in js)

# 4. JS 无旧函数残留
for old in ['loadContainerConfig', 'saveContainerConfig', 'testContainerConfig']:
    check(f'JS 无 {old} 残留', old not in js)

# 5. schema API 返回完整分类
print('--- config-center API ---')
r4 = urllib.request.urlopen(f'{BASE}/api/config-center/schema')
schema_resp = json.loads(r4.read().decode('utf-8'))
categories = list((schema_resp.get('data') or {}).keys())
check(f'schema 返回 {len(categories)} 个分类: {categories}', len(categories) >= 6)

# 6. values API 正常
r5 = urllib.request.urlopen(f'{BASE}/api/config-center/values')
vals_resp = json.loads(r5.read().decode('utf-8'))
check('values API 响应正常', vals_resp.get('code') == 0)

print()
if all_ok:
    print('全部验证通过! 系统配置 tab 已完整集成到调度中心仪表盘')
else:
    print('存在未通过项，请检查')
