"""验证容器中心连接 tab 在调度中心仪表盘上的集成"""

import urllib.request

BASE = 'http://127.0.0.1:5000'

def check(label, actual, expected):
    ok = actual == expected
    print(f'  [{"OK" if ok else "FAIL"}] {label}')
    return ok

def check_contains(label, content, pattern):
    ok = pattern in content
    print(f'  [{"OK" if ok else "FAIL"}] {label}')
    return ok

all_ok = True

# 1. 验证 HTML 页面
print('--- dispatch_center.html ---')
r = urllib.request.urlopen(f'{BASE}/api/dispatch-center/')
html = r.read().decode('utf-8')

html_checks = [
    ('sidebar 容器中心连接', 'container-config'),
    ('tab-content 容器中心连接', 'id="tab-container-config"'),
    ('服务地址输入框', 'id="cc-url"'),
    ('连接密钥输入框', 'id="cc-secret"'),
    ('保存配置按钮', 'saveContainerConfig'),
    ('测试连接按钮', 'testContainerConfig'),
    ('连接状态指示', 'id="cc-status"'),
]

for label, pattern in html_checks:
    ok = check_contains(label, html, pattern)
    if not ok: all_ok = False

# 2. 验证 CSS
print('--- dispatch_center.css ---')
r2 = urllib.request.urlopen(f'{BASE}/static/css/dispatch_center.css')
css = r2.read().decode('utf-8')
ok = check('CSS 加载 (' + str(len(css)) + ' chars)', True, len(css) > 0)
if not ok: all_ok = False

# 3. 验证 JS
print('--- dispatch_center.js ---')
r3 = urllib.request.urlopen(f'{BASE}/static/js/dispatch_center.js')
js = r3.read().decode('utf-8')

js_checks = ['loadContainerConfig', 'saveContainerConfig', 'testContainerConfig', 'container-config']
for fn in js_checks:
    ok = check_contains('JS 包含 ' + fn, js, fn)
    if not ok: all_ok = False

# 4. 验证 JS 无残留 script 标签
ok = check_contains('JS 无残留 </script>', js, '</script>')
if ok:
    print('  [FAIL] JS 仍有残留 </script> 标签!')
    all_ok = False
else:
    print('  [OK] JS 无残留 </script> 标签')

# 5. 验证后端 schema 接口
print('--- config_center schema ---')
r4 = urllib.request.urlopen(f'{BASE}/api/config-center/schema')
schema = r4.read().decode('utf-8')
schema_checks = [
    ('schema 包含 CONTAINER_CENTER_URL', 'CONTAINER_CENTER_URL'),
    ('schema 包含 CONTAINER_CENTER_SECRET', 'CONTAINER_CENTER_SECRET'),
    ('schema 包含 test action', 'container_center'),
]
for label, pattern in schema_checks:
    ok = check_contains(label, schema, pattern)
    if not ok: all_ok = False

print()
if all_ok:
    print('全部验证通过! 容器中心连接 tab 已成功集成到调度中心仪表盘')
else:
    print('存在未通过项，请检查')
